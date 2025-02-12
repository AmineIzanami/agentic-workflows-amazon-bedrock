# tests/conftest.py
import pytest
from aws_cdk import App
from aws_cdk import Environment

@pytest.fixture(scope="function")
def app():
    return App()

@pytest.fixture(scope="function")
def env():
    return Environment(
        account="123456789012",  # Use a test account number
        region="us-east-1"
    )

@pytest.fixture(scope="function")
def mock_agent_action_group_property():
    # Mock for CfnAgent.AgentActionGroupProperty
    return {
        'actionGroupName': 'MockActionGroup',
        'actionGroupExecutor': {
            'lambda': 'arn:aws:lambda:us-east-1:123456789012:function:example-function'
        },
        'functionSchema': {
            'functions': [
                {
                    'name': 'mockFunction1',
                    'description': 'Mock function description',
                    'parameters': {
                        'Param1': {
                            'description': 'Description of parameter 1',
                            'required': True,
                            'type': 'string'
                        }
                    }
                }
            ]
        },
        'description': 'Mock action group for testing purposes'
    }