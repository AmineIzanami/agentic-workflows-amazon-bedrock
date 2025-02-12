from dataclasses import dataclass
from typing import Dict, Optional, List
from aws_cdk.aws_bedrock import CfnAgent, CfnKnowledgeBase
from stacks.kb_infra_stack import KbInfraStack
import re



@dataclass
class Reply_Agent:
    agent_name: str
    instruction: str
    agent_description: str = None
    collaborator_order: Optional[int] = None
    activate: bool = True
    to_collaborate: bool = False
    supervisor: bool = False
    use_knowledge_base: bool = False
    foundation_model: Optional[str] = None
    collaborator_instruction: Optional[str] = None
    agent_action_group: List[CfnAgent.AgentActionGroupProperty] = None
    agent_resource_role_arn: str = None
    agent_id: str = None
    agent_version: str = "DRAFT"
    agent_alias_id: str = None
    agent_alias_arn: str = None
    knowledge_base: CfnKnowledgeBase = None
    tags: Optional[Dict[str, str]] = None

    @property
    def synthesized_agent_name(self) -> str:
        """
        Returns a normalized agent name by removing spaces, underscores, and hyphens, and converting it to lowercase.
        """
        return re.sub(r"[\s_-]+", "", self.agent_name).lower()
