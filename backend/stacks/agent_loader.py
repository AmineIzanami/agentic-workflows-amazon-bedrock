from pathlib import Path
from typing import Dict

import yaml
from aws_cdk import (
    aws_iam as iam
)
from aws_cdk.aws_bedrock import CfnKnowledgeBase, CfnAgent

from stacks import Reply_Agent

import logging

logger = logging.getLogger(__name__)


class AgentLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._config_data = None
        self._load_config()

    def _load_config(self):
        """Load the YAML configuration file into memory."""
        with open(self.config_path, 'r') as file:
            self._config_data = yaml.safe_load(file)

    def get_project_name(self) -> str:
        """Return the project name from the configuration."""
        if self._config_data:
            return self._config_data.get("project_name", "")
        return ""

    def load_agents(self, *,
                    agent_resource_role: iam.Role,
                    agent_available_tools: Dict[str, CfnAgent.AgentActionGroupProperty],
                    knowledge_base: CfnKnowledgeBase = None
                    ):
        """Load agent configurations and return them as a dictionary."""
        project_name = self.get_project_name()
        agents_config = self._config_data.get("agents", {})
        reply_agents = {}

        # Track the number of supervisors in the configuration
        supervisor_count = 0

        for key, settings in agents_config.items():
            if settings.get("supervisor", False):
                supervisor_count += 1

            # Substitute project name in agent_name
            agent_name = settings["agent_name"].replace("${project_name}", project_name)
            agent_action_group = self.resolve_action_group(settings.get("agent_action_group", []))
            instruction_content = self.read_instruction_file(settings["instruction_file"])

            reply_agent = Reply_Agent(
                agent_name=agent_name,
                instruction=instruction_content,
                collaborator_order=settings.get("collaborator_order", 0),
                activate=settings.get("activate", False),
                to_collaborate=settings.get("to_collaborate", False),
                foundation_model=settings["foundation_model"],
                knowledge_base=knowledge_base,
                agent_action_group=[agent_available_tools.get(_key_agent_action_group) for _key_agent_action_group in
                                    agent_action_group],
                agent_resource_role_arn=agent_resource_role.role_arn,
                collaborator_instruction=settings.get("collaborator_instruction"),
                supervisor=settings.get("supervisor", False),
            )

            reply_agents[key] = reply_agent
            logger.info(f"Agent {key} Loaded with Settings {settings}")
        # Ensure only one supervisor exists
        if supervisor_count != 1:
            raise ValueError(f"Only one supervisor should exist. Found {supervisor_count} supervisors.")

        return reply_agents

    def read_instruction_file(self, file_name):
        path = Path("./stacks/prompts") / file_name
        with open(path, 'r') as file:
            return file.read().strip()

    def resolve_action_group(self, action_group_keys):
        # Logic to resolve and return the appropriate action groups
        return action_group_keys

    def resolve_role_arn(self, role_arn_key):
        # Logic to resolve and return the appropriate role arn
        return role_arn_key

# Example usage
# loader = AgentLoader("path/to/agent_config.yaml")
# project_name = loader.get_project_name()
# print(f"Project Name: {project_name}")
