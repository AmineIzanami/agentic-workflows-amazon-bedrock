"""Main application module for the agentic chatbot interface."""

import asyncio
import os
from io import BytesIO
from pathlib import Path
from typing import Optional

import streamlit as st
from streamlit_cognito_auth import CognitoHostedUIAuthenticator

from agent.agent import Agent
from components.feedback import render_feedback_ui
from components.sidebar import render_sidebar
from components.style import apply_custom_style
from core.auth import Auth
from core.langfuse_client import create_langfuse_client
from core.s3 import S3Handler
from core.session import SessionManager
from streamlit.runtime.scriptrunner import get_script_run_ctx
from dotenv import load_dotenv
import traceback

import os
import boto3
from botocore.exceptions import ClientError


# load_dotenv()

def load_ssm_parameters_to_env(parameters_name, region_name="us-east-1"):
    """
    Load specified SSM parameters and set them as environment variables.

    Args:
    - parameter_names: List of parameter names to load from SSM.
    - region_name: AWS region where the SSM parameters are stored.

    Raises:
    - ClientError: If there's an error retrieving parameters from SSM.
    """
    ssm_client = boto3.client('ssm', region_name=region_name)

    try:
        for _p in parameters_name:
            response = ssm_client.get_parameter(
                Name=_p,
                WithDecryption=True if "SECRET" in _p or "KEY" in _p else False
            )

            parameters = response['Parameter']
            invalid_parameters = response.get('InvalidParameters')

            if invalid_parameters:
                raise ValueError(f"Invalid parameters found: {invalid_parameters}")

            value = parameters['Value']
            _env_key = parameters['Name'].split("/")[-1]
            os.environ[_env_key] = value
            print(f"Set environment variable {_env_key} to {value}")

    except ClientError as e:
        print(f"Failed to retrieve parameters: {str(e)}")
        raise


def display_message_images(images: list) -> None:
    """Display images associated with a message."""
    if not images:
        return

    with st.expander("Generated Images", True):
        for image in images:
            try:
                image_data = BytesIO(image["bytes"])
                st.image(image_data, caption=image.get("name", ""))
            except Exception as e:
                st.error(f"Failed to display image {image.get('name', '')}: {str(e)}")


def display_message_html(html_files: list) -> None:
    """Display HTML files associated with a message."""
    if not html_files:
        return

    with st.expander("Generated HTML", True):
        for html_file in html_files:
            try:
                st.markdown(f"**{html_file.get('name', '')}**")
                # Add wrapper div and script to calculate height
                wrapped_content = f"""
                    <div id="html-wrapper" style="min-height: 250px;">
                        {html_file["content"]}
                    </div>
                    <script>
                        // Wait for the content to load
                        window.addEventListener('load', function() {{
                            // Get the wrapper element
                            var wrapper = document.getElementById('html-wrapper');
                            // Get the actual height of the content
                            var height = Math.max(250, wrapper.scrollHeight);
                            // Set the iframe height through Streamlit
                            window.parent.postMessage({{
                                type: 'streamlit:setFrameHeight',
                                height: height
                            }}, '*');
                        }});
                    </script>
                """
                st.components.v1.html(wrapped_content, scrolling=True, height=250)
            except Exception as e:
                st.error(f"Failed to display HTML {html_file.get('name', '')}: {str(e)}")


async def initialize_session(auth: Optional[Auth] = None) -> CognitoHostedUIAuthenticator:
    """Initialize the user session and handle authentication."""


    if not auth:
        auth = Auth()
    authenticator = auth.get_authenticator()
    is_logged_in = authenticator.login()
    if not is_logged_in:
        st.stop()
    return authenticator


async def handle_chat_interaction(
        agent: Agent,
        username: str,
        session_manager: SessionManager,
        prompt: str,
        s3_handler: S3Handler
) -> None:
    """Handle a single chat interaction between the user and the agent."""
    session_manager.add_user_message(content=prompt, s3_handler=s3_handler)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            trace_id = session_manager.create_trace(username, prompt)
            with st.spinner("Agent is thinking.."):
                response = agent.invoke_agent(
                    messages=session_manager.messages,
                    user_id=username,
                    session_id=session_manager.session_id,
                    session_manager=session_manager,
                    s3_handler=s3_handler,
                    uploaded_files=session_manager.uploaded_files,
                    trace_id=trace_id,
                )
            st.write(response)
            display_message_images(session_manager.get_message_images(trace_id))
            display_message_html(session_manager.get_message_html(trace_id))
            render_feedback_ui(trace_id, session_manager)
        except Exception as ex:
            st.error(f"Something went wrong: {str(ex)}")
            tb_str = traceback.format_exc()

            # Display traceback in an expandable section
            with st.expander("Show Traceback"):
                st.text(tb_str)


def return_reply_svg():
    return """<?xml version="1.0" encoding="UTF-8"?>
<svg id="Livello_1" data-name="Livello 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 613.97 190.97">
  <defs>
    <style>
      .cls-1 {
        fill: #024854;
      }

      .cls-1, .cls-2 {
        stroke-width: 0px;
      }

      .cls-2 {
        fill: #cad405;
      }
    </style>
  </defs>
  <g id="Logo">
    <g id="RUNNING_MAN" data-name="RUNNING MAN">
      <g>
        <path class="cls-2" d="M146.97,0c-9.06,0-16.39,7.35-16.39,16.42s7.32,16.38,16.39,16.38,16.39-7.33,16.39-16.38S156.01,0,146.97,0Z"/>
        <path class="cls-2" d="M111.03,68.97l20.47-26.95c1.05-1.38,1.13-3.26.22-4.73l-8.7-13.95c-.77-1.23-2.12-1.97-3.57-1.96l-37.53.26h0l-20.58-.02c-1.61,0-2.33,2.02-1.07,3.04l5.77,4.65c.81.65,1.77,1.1,2.8,1.29l35.74,6.73-44.22,47.52L2.17,93.11c-2.02.29-2.88,2.72-1.49,4.21l5.68,6.1c1.12,1.21,2.71,1.88,4.36,1.85l56.18-.92c2.08-.03,4.11-.62,5.89-1.71l13.46-8.2,28.41,22.55c1.12.89,1.85,2.17,2.04,3.59l5.41,39.82c.25,1.88,1.86,3.28,3.75,3.28h2.89c2.09,0,3.78-1.69,3.79-3.77l.17-44.19c0-2.28-.72-4.5-2.08-6.33l-24.79-33.41,5.18-7.01Z"/>
      </g>
    </g>
    <g>
      <path class="cls-1" d="M252.47,125.33l-19.37-35.04h-15.38v35.04h-21V26.71h46.13c20.55,0,33.27,13.45,33.27,31.79,0,17.3-11.09,26.76-21.73,29.28l22.33,37.56h-24.25ZM254.54,58.35c0-8.13-6.36-13.16-14.64-13.16h-22.18v26.61h22.18c8.28,0,14.64-5.03,14.64-13.45Z"/>
      <path class="cls-1" d="M291.8,125.33V26.71h69.79v18.48h-48.79v20.7h47.76v18.48h-47.76v22.47h48.79v18.48h-69.79Z"/>
      <path class="cls-1" d="M377.99,125.33V26.71h46.13c21.44,0,33.12,14.49,33.12,31.79s-11.83,31.64-33.12,31.64h-25.14v35.19h-20.99ZM435.8,58.49c0-8.28-6.36-13.31-14.64-13.31h-22.18v26.47h22.18c8.28,0,14.64-5.03,14.64-13.16Z"/>
      <path class="cls-1" d="M469.51,125.33V26.71h21.14v80.14h41.7v18.48h-62.84Z"/>
      <path class="cls-1" d="M555.27,125.33v-40.36l-37.85-58.26h23.95l24.4,39.48,24.4-39.48h23.81l-37.7,58.26v40.36h-21Z"/>
    </g>
    <g>
      <path class="cls-2" d="M196.71,190.97v-41.09h15.28c12.87,0,21.5,8.5,21.5,20.51s-8.62,20.57-21.44,20.57h-15.34ZM226.09,170.4c0-7.88-4.93-14.17-14.04-14.17h-8.13v28.4h8.07c8.93,0,14.11-6.41,14.11-14.23Z"/>
      <path class="cls-2" d="M267.12,190.97l-3.02-7.95h-18.85l-3.02,7.95h-8.19l16.14-41.09h8.99l16.14,41.09h-8.19ZM254.67,157.09l-7.39,19.59h14.78l-7.39-19.59Z"/>
      <path class="cls-2" d="M285.54,190.97v-34.74h-12.44v-6.34h32.09v6.34h-12.44v34.74h-7.21Z"/>
      <path class="cls-2" d="M336.11,190.97l-3.02-7.95h-18.85l-3.02,7.95h-8.19l16.14-41.09h8.99l16.14,41.09h-8.19ZM323.67,157.09l-7.39,19.59h14.78l-7.39-19.59Z"/>
    </g>
  </g>
</svg>"""


async def main() -> None:
    """Main application entry point.

    Sets up the Streamlit interface, initializes core services,
    handles authentication, and manages the chat interface.
    """
    st.set_page_config(
        page_title="Reply SoW Agent",
        page_icon="🤖",
        menu_items={},
    )

    apply_custom_style()

    if st.get_option("client.toolbarMode") != "minimal":
        st.set_option("client.toolbarMode", "minimal")
        await asyncio.sleep(0.1)
        st.rerun()

    # Initialize session and auth
    authenticator = await initialize_session()
    username = authenticator.get_username()

    # Initialize core services
    session_manager = SessionManager(
        session_id=get_script_run_ctx().session_id,  # type: ignore
        langfuse=create_langfuse_client(),
        authenticator=authenticator
    )
    agent = Agent(langfuse=session_manager.langfuse)
    s3_handler = S3Handler()
    # Render UI components
    render_sidebar(authenticator, session_manager, s3_handler, )

    # Display chat history
    for message in session_manager.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                if "trace_id" in message:
                    display_message_images(session_manager.get_message_images(message["trace_id"]))
                    display_message_html(session_manager.get_message_html(message["trace_id"]))
                    render_feedback_ui(message["trace_id"], session_manager)

    # Handle new chat input
    if prompt := st.chat_input("How can I help you today?"):
        if len(session_manager.uploaded_files) == 0:
            st.error("Error: You need to upload the SOW document first!")
            st.stop()

        await handle_chat_interaction(agent=agent,
                                      username=username,
                                      session_manager=session_manager,
                                      prompt=prompt,
                                      s3_handler=s3_handler)


if __name__ == "__main__":
    parameter_to_be_loaded = [
        "SUPERVISOR_AGENT_ID",
        "SUPERVISOR_AGENT_ALIAS_ID",
        "BEDROCK_REGION",
        "RAG_BUCKET_NAME",
        "SOW_BUCKET_NAME",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
        "USER_POOL_ID",
        "USER_POOL_CLIENT_ID",
        "USER_POOL_CLIENT_SECRET",
        "USER_POOL_COGNITO_DOMAIN",
        "USER_POOL_REDIRECT_URI"
    ]

    load_ssm_parameters_to_env(
        parameters_name=["/multiagent/streamlit/configuration/" + _p for _p in parameter_to_be_loaded],
        region_name=os.getenv("MULTI_AGENT_REGION")
    )

    asyncio.run(main())
