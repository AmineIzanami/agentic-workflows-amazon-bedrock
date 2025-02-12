# tests/unit/test_agent_loader.py

import pytest
from stacks.agent_loader import AgentLoader
from unittest.mock import patch, mock_open, MagicMock
from aws_cdk import aws_iam as iam
from aws_cdk.aws_bedrock import CfnAgent

# Sample YAML data to be used for mocking file read
mock_yaml_data = """
project_name: TestProject
agents:
  analyse_image_sow:
    agent_name: "${project_name}-AnalyseImageSoW"
    instruction_file: "PDFImageAnalyzer.xml"
    collaborator_order: 0
    activate: true
    to_collaborate: true
    foundation_model: "SomeModel"
    knowledge_base: true
    agent_action_group: ["group1"]
    agent_resource_role_arn: "arn:aws:iam::123456789012:role/example"
    collaborator_instruction: "Instruction for image sow"
"""

@pytest.fixture
def mock_agent_resource_role():
    # Create a mock IAM Role
    return MagicMock(spec=iam.Role, role_arn="arn:aws:iam::123456789012:role/test-role")

@pytest.fixture
def mock_agent_available_tools():
    # Create a mock for AgentActionGroupProperty
    mock_action_group = MagicMock(spec=CfnAgent.AgentActionGroupProperty)
    return {"group1": mock_action_group}

def test_loader_initialization():
    with patch("stacks.agent_loader.open", mock_open(read_data=mock_yaml_data)):
        loader = AgentLoader("mock_agent_config.yaml")
        assert loader._config_data is not None, "Config data should be loaded"

def test_get_project_name():
    with patch("stacks.agent_loader.open", mock_open(read_data=mock_yaml_data)):
        loader = AgentLoader("mock_agent_config.yaml")
        project_name = loader.get_project_name()
        assert project_name == "TestProject", "Project name should match the mocked data"

def test_load_agents(mock_agent_resource_role, mock_agent_available_tools):
    with patch("stacks.agent_loader.open", mock_open(read_data=mock_yaml_data)), \
         patch("stacks.agent_loader.Path.open", mock_open(read_data="Mock Instruction Content")):

        loader = AgentLoader("mock_agent_config.yaml")
        agents = loader.load_agents(
            agent_resource_role=mock_agent_resource_role,
            agent_available_tools=mock_agent_available_tools
        )

        assert "analyse_image_sow" in agents, "The analyse_image_sow agent should be loaded"

        agent = agents["analyse_image_sow"]
        assert agent.agent_name == "TestProject-AnalyseImageSoW", "Agent name should be correctly constructed"
        assert agent.activate, "Agent should be active"
        assert agent.agent_action_group[0] == mock_agent_available_tools["group1"], "Agent action group should be correctly resolved"