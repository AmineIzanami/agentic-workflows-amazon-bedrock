"""Sidebar UI component."""

import time
from typing import List, Tuple

import streamlit as st
from streamlit_cognito_auth import CognitoHostedUIAuthenticator

from core.s3 import S3Handler
from core.session import SessionManager


def _render_user_info(authenticator: CognitoHostedUIAuthenticator, session_id: str,
                      session_manager: SessionManager) -> None:
    st.markdown(
        f"""
        **Username**: {authenticator.get_username()}\n
        **Session ID**: {session_id}
        """
    )
    if st.button("Reset Session", key="reset_session"):
        session_manager.reset()
        st.success("Session reset successfully!")
        time.sleep(2)
        st.rerun()

    if st.button("Logout", key="cognito_logout_btn"):
        logout(authenticator)


def _render_file_uploader(session_manager: SessionManager, s3_handler: S3Handler) -> None:
    from docx import Document
    uploaded_files = st.file_uploader(
        label="**SoW Documents to be included in your query:**",
        type=["pdf"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        for file in uploaded_files:
            if file:
                try:
                    s3_handler.upload_to_s3(file, session_manager=session_manager)
                    st.success(f"File '{file.name}' uploaded to '{s3_handler.sow_bucket_name}'")
                except Exception as er:
                    st.error(f"Error uploading file '{file.name}' : {er}")

    session_manager.set_uploaded_files(uploaded_files or [])


def logout(authenticator: CognitoHostedUIAuthenticator):
    print("Logout From SoW Validator")
    authenticator.logout()


def render_sidebar(authenticator: CognitoHostedUIAuthenticator, session_manager: SessionManager,
                   s3_handler: S3Handler) -> None:
    """Render the sidebar UI component with all its sections.

    Args:
        username: The current user's username
        session_manager: Session management instance
        s3_handler: S3 operations handler
    """
    with st.sidebar:
        _render_user_info(authenticator, session_manager.session_id, session_manager)
        st.divider()
        _render_file_uploader(session_manager, s3_handler)
