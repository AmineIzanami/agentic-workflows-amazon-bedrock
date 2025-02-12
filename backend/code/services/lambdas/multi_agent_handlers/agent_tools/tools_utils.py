import base64
import io
import json
import re
from io import BytesIO
from urllib.parse import urlparse

import boto3
import fitz  # PyMuPDF for PDF processing
from docx import Document
import os


s3_client = boto3.client("s3")

SECTION_PATTERNS = {
    "SOLUTION ARCHITECTURE / ARCHITECTURAL DIAGRAM": re.compile(
        r"SOLUTION\s+ARCHITECTURE\s*/\s*ARCHITECTURAL\s+DIAGRAM", re.IGNORECASE),
    "SUMMARY OF MILESTONES & DELIVERABLES": re.compile(r"SUMMARY\s+OF\s+MILESTONES\s*&\s*DELIVERABLES", re.IGNORECASE)
}


def read_s3_url(s3_url_path):
    """Reads a file from S3 and extracts text if it's a PDF"""
    parsed_url = urlparse(s3_url_path)
    if not parsed_url.netloc or not parsed_url.path:
        return {"error": "Invalid S3 URL format"}

    bucket_name = parsed_url.netloc
    s3_key = parsed_url.path.lstrip("/")

    response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
    file_data = response["Body"].read()
    file_extension = s3_key.lower().split(".")[-1]

    # Extract text based on file type
    if file_extension == "pdf":
        extracted_text = extract_text_from_pdf(file_data)
    elif file_extension in ["docx", "doc"]:
        extracted_text = extract_text_from_docx(file_data)
    else:
        try:
            extracted_text = file_data.decode("utf-8")
        except UnicodeDecodeError:
            extracted_text = base64.b64encode(file_data).decode("utf-8")

    print(f"Extracted Text: {extracted_text[:500]}")  # Print first 500 chars for debugging
    return extracted_text


def extract_text_from_pdf(pdf_bytes):
    """Extracts text from a PDF file."""
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(page.get_text() for page in pdf_document)
    return text


def extract_text_from_docx(doc_bytes):
    """Extracts text from a Word (.docx) file."""
    doc_stream = io.BytesIO(doc_bytes)
    doc = Document(doc_stream)
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    return text


def llm_describe_image(image_base64):
    """Calls Bedrock LLM to analyze an image."""
    bedrock = boto3.client(service_name='bedrock-runtime', region_name="us-east-1")
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": os.environ["ANALYSE_AWS_DIAGRAM_AGENT_PROMPT"]
                    }
                ]
            }
        ]
    }
    print(f" ##### Analysing Image #####")
    response = bedrock.invoke_model(
        body=json.dumps(request_body),
        modelId=os.environ['LLM_MODEL_AGENT'],
        contentType="application/json",
        accept="application/json"
    )
    response_body = json.loads(response['body'].read())
    analysis = response_body['content'][0]['text']
    return analysis


def parse_s3_uri(s3_uri):
    """Extract bucket name and key from S3 URI (s3://bucket-name/path/to/file.pdf)"""
    match = re.match(r"s3://([^/]+)/(.+)", s3_uri)
    if not match:
        raise ValueError("Invalid S3 URI format. Expected format: s3://bucket-name/path/to/file.pdf")
    return match.group(1), match.group(2)


def download_document_from_s3(s3_uri):
    """Download a PDF file from S3 and return it as a BytesIO object."""
    bucket_name, file_key = parse_s3_uri(s3_uri)
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return BytesIO(response["Body"].read())


def extract_images_from_pdf_sections(pdf_stream):
    """Extract images from sections sequentially and associate them with the most recent section title."""
    doc = fitz.open(stream=pdf_stream, filetype="pdf")
    image_data = []
    current_section = None

    for page_num, page in enumerate(doc, start=1):
        if page_num < 3:
            continue
        text = page.get_text("text")  # Extract full text from the page

        # Check if we are entering a new section
        for section_name, pattern in SECTION_PATTERNS.items():
            if pattern.search(text):
                current_section = section_name  # Switch to the new section
                print(f"Detected Section: {current_section} on Page {page_num}")

        # Extract images and assign them to the current section
        if current_section:
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                base64_image = base64.b64encode(image_bytes).decode("utf-8")

                image_data.append({
                    "page": page_num,
                    "image_index": img_index,
                    "image_base64": base64_image
                })

    return image_data
