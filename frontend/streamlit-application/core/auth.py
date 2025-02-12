"""Authentication module for handling Cognito user authentication."""

import os

from streamlit_cognito_auth import CognitoAuthenticator
from streamlit_cognito_auth import CognitoHostedUIAuthenticator

class Auth:
    """Authentication handler for AWS Cognito integration."""

    def __init__(self) -> None:
        """Initialize the authentication handler with Cognito configuration."""

        authenticator = CognitoHostedUIAuthenticator(
            pool_id=os.getenv("USER_POOL_ID"),
            app_client_id=os.getenv("USER_POOL_CLIENT_ID"),
            app_client_secret=os.getenv("USER_POOL_CLIENT_SECRET"),
            cognito_domain=os.getenv("USER_POOL_COGNITO_DOMAIN"),
            redirect_uri=os.getenv("USER_POOL_REDIRECT_URI"),
            use_cookies=False
        )

        self.authenticator = authenticator

    def get_authenticator(self) -> CognitoHostedUIAuthenticator:
        """Get the configured Cognito authenticator instance."""
        return self.authenticator
