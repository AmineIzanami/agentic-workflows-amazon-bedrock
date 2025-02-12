from agent_tools.tools_utils import (
    read_s3_url,
    download_document_from_s3,
    extract_images_from_pdf_sections,
    llm_describe_image
)
import json




def lambda_handler(event, context):
    """AWS Lambda handler function."""
    print(event)
    agent = event.get('agent')
    actionGroup = event.get('actionGroup')
    function = event.get('function')
    parameters = event.get('parameters', [])
    response_body = {
        "TEXT": {
            "body": "Error, no function was called"
        }
    }

    if function == 'get_document_from_s3':
        s3_uri_path = None
        for param in parameters:
            if param["name"] == "s3_uri_path":
                s3_uri_path = param["value"]

        if not s3_uri_path:
            raise Exception("Missing mandatory parameter: s3_uri_path")

        try:
            document_content = read_s3_url(s3_uri_path)
            response_body = {
                'TEXT': {
                    "body": document_content
                }
            }
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            response_body = {
                'TEXT': {
                    "body": f"An error occurred while processing the file: {str(e)}"
                }
            }

    if function == 'analyse_images_documents':
        s3_uri_path = None
        for param in parameters:
            if param["name"] == "s3_uri_path":
                s3_uri_path = param["value"]

        if not s3_uri_path:
            raise Exception("Missing mandatory parameter: s3_uri_path")

        try:
            doc_stream = download_document_from_s3(s3_uri_path)
            images_details = extract_images_from_pdf_sections(doc_stream)
            # create new dict with the details from image_details page, image_index and image describe that is the call of function on image_base64
            images_described = [{"page": image["page"],
                                 "image_index": image["image_index"],
                                 "image_described": llm_describe_image(image["image_base64"])} for image in images_details]

            response_body = {
                'TEXT': {
                    "body": json.dumps(images_described)
                }
            }
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            response_body = {
                'TEXT': {
                    "body": f"An error occurred while processing the file: {str(e)}"
                }
            }
    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': response_body
        }
    }

    function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    print("Response:", json.dumps(function_response, indent=2))
    return function_response

