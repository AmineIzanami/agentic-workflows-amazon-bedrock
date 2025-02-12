import traceback
from collections import OrderedDict
import logging

logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

import boto3

from backend.fail_fast_boto3.utils_multi_agent_bedrock import multi_agent_manager

# AWS Configuration
paris_bedrock_region = "eu-west-3"
us_bedrock_region = "us-east-1"

# Initialize the Boto3 Session
boto3_session = boto3.Session(region_name=paris_bedrock_region)
bedrock_agent_client = boto3_session.client('bedrock-agent')
bedrock_agent_runtime_client = boto3_session.client('bedrock-agent-runtime')

if __name__ == "__main__":
    mode = "delete"  ## "create" or "delete"
    if mode == "create":
        try:
            # Parameters
            role_arn = "<your_role_arn>"  # need to have permissions on bedrock full permission fo testing
            anthropic_sonnet_foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"
            anthropic_haiku_foundation_model = "anthropic.claude-3-haiku-20240307-v1:0"
            amazon_pro_foundation_model = "amazon.nova-pro-v1:0"
            amazon_lite_foundation_model = "amazon.nova-lite-v1:0"
            foundation_model = anthropic_sonnet_foundation_model
            ai_factory_knowledge_base_id = "<your_kb_id>"
            kb_description = " Knowledge base for domain-specific information."

            # Tags
            shared_tags = {
                'Owner': 'Amine',
                'Environment': 'Dev',
                'BusinessUnit': 'DataReplyFrance',
                'CostCenter': 'DataReply'
            }

            # Paths to the XML templates
            xml_files = {
                "StructuralComplianceAgent": "./prompts/StructuralComplianceAgent.xml",
                "TechnicalScopeValidationAgent": "./prompts/TechnicalScopeValidationAgent.xml",
                "BusinessFinancialValidationAgent": "./prompts/BusinessFinancialValidationAgent.xml",
                "RiskComplianceAgent": "./prompts/RiskComplianceAgent.xml",
                "DeliveryMilestonesValidationAgent": "./prompts/DeliveryMilestonesValidationAgent.xml",
                "AIConsistencyAgent": "./prompts/AIConsistencyAgent.xml",
                "AWSArchitectureValidationAgent": "./prompts/AWSArchitectureValidationAgent.xml",  # New agent
                "SupervisorAgent": "./prompts/SupervisorAgent.xml",
                "SingleAgentSowValidator": "./prompts/SingleAgentSowValidator.xml",
            }

            # Define project name
            project_name = "sow-validator"
            agent_get_s3_file = dict(
                function_arn="<your_function_arn>",
                agent_action_group_name="lambda_processing_sow",
                agent_action_description="Responsible of calling the lambda function to download the S3 url and return the content of the files ",
                agent_functions=[{
                    'name': 'get_document_from_s3',
                    'description': 'the S3 url to use to download the Statement of work from S3',
                    'parameters': {
                        "s3_uri_path": {
                            "description": "the S3 uri of the original statement of work",
                            "required": True,
                            "type": "string"
                        }
                    }
                }])

            all_action_groups_agent_functions = dict(
                structural_compliance=[agent_get_s3_file],
                technical_scope_validation=[agent_get_s3_file],
                business_financial_validation=[agent_get_s3_file],
                risk_compliance=[agent_get_s3_file],
                delivery_milestones_validation=[agent_get_s3_file],
                ai_consistency=[agent_get_s3_file],
            )
            import re


            def remove_xml_tags(xml_content):
                # return xml_content
                """Removes all XML tags from a given string"""
                return re.sub(r'<[^>]+>', '', xml_content)


            # Example usage
            xml_data = multi_agent_manager.read_xml_content(xml_files["StructuralComplianceAgent"])

            # Define sub-agents
            agents = {
                "structural_compliance": {
                    "agent_name": f"{project_name}-StructuralComplianceAgent",
                    "instruction": remove_xml_tags(
                        multi_agent_manager.read_xml_content(xml_files["StructuralComplianceAgent"])),
                    "collaborator_order": 0,
                    "activate": True,
                    "to_collaborate": True,
                    "use_knowledge_base": False,
                    "collaborator_instruction": "Call this agent to validate the structure and format of the SoW document.",
                    "tags": {**shared_tags, 'WorkloadName': f'{project_name}-StructuralComplianceAgent'}
                },
                "technical_scope_validation": {
                    "agent_name": f"{project_name}-TechnicalScopeValidationAgent",
                    "instruction": remove_xml_tags(
                        multi_agent_manager.read_xml_content(xml_files["TechnicalScopeValidationAgent"])),
                    "collaborator_order": 1,
                    "activate": True,
                    "to_collaborate": True,
                    "use_knowledge_base": False,
                    "collaborator_instruction": "Call this agent to validate the technical feasibility of the SoW.",
                    "tags": {**shared_tags, 'WorkloadName': f'{project_name}-TechnicalScopeValidationAgent'}
                },
                "business_financial_validation": {
                    "agent_name": f"{project_name}-BusinessFinancialValidationAgent",
                    "instruction": multi_agent_manager.read_xml_content(xml_files["BusinessFinancialValidationAgent"]),
                    "collaborator_order": 2,
                    "activate": True,
                    "to_collaborate": True,
                    "use_knowledge_base": False,
                    "collaborator_instruction": "Call this agent to verify the financial details, investment, and cost breakdown of the SoW.",
                    "tags": {**shared_tags, 'WorkloadName': f'{project_name}-BusinessFinancialValidationAgent'}
                },
                "risk_compliance": {
                    "agent_name": f"{project_name}-RiskComplianceAgent",
                    "instruction": multi_agent_manager.read_xml_content(xml_files["RiskComplianceAgent"]),
                    "collaborator_order": 3,
                    "activate": True,
                    "to_collaborate": True,
                    "use_knowledge_base": False,
                    "collaborator_instruction": "Call this agent to analyze potential risks and compliance issues within the SoW.",
                    "tags": {**shared_tags, 'WorkloadName': f'{project_name}-RiskComplianceAgent'}
                },
                "delivery_milestones_validation": {
                    "agent_name": f"{project_name}-DeliveryMilestonesValidationAgent",
                    "instruction": multi_agent_manager.read_xml_content(xml_files["DeliveryMilestonesValidationAgent"]),
                    "collaborator_order": 4,
                    "activate": True,
                    "to_collaborate": True,
                    "use_knowledge_base": False,
                    "collaborator_instruction": "Call this agent to ensure the project milestones and deliverables are realistic and well-defined.",
                    "tags": {**shared_tags, 'WorkloadName': f'{project_name}-DeliveryMilestonesValidationAgent'}
                },
                "ai_consistency": {
                    "agent_name": f"{project_name}-AIConsistencyAgent",
                    "instruction": multi_agent_manager.read_xml_content(xml_files["AIConsistencyAgent"]),
                    "collaborator_order": 5,
                    "activate": True,
                    "to_collaborate": True,
                    "use_knowledge_base": False,
                    "collaborator_instruction": "Call this agent to validate AI-related elements within the SoW, including model selection and feasibility.",
                    "tags": {**shared_tags, 'WorkloadName': f'{project_name}-AIConsistencyAgent'}
                },
                "aws_architecture_validation": {  # New AWS Diagram Validation Agent
                    "agent_name": f"{project_name}-AWSArchitectureValidationAgent",
                    "instruction": multi_agent_manager.read_xml_content(xml_files["AWSArchitectureValidationAgent"]),
                    "collaborator_order": 6,
                    "activate": False,
                    "to_collaborate": True,
                    "use_knowledge_base": False,
                    "collaborator_instruction": "Call this agent to validate AWS architecture diagrams, extract AWS service details, and check compliance with best practices.",
                    "tags": {**shared_tags, 'WorkloadName': f'{project_name}-AWSArchitectureValidationAgent'}
                },
                "supervisor": {
                    "agent_name": f"{project_name}-SupervisorAgent",
                    "instruction": remove_xml_tags(multi_agent_manager.read_xml_content(xml_files["SupervisorAgent"])),
                    "activate": True,
                    "use_knowledge_base": False,
                    "tags": {**shared_tags, 'WorkloadName': f'{project_name}-SupervisorAgent'}
                }
            }

            # Step 1: Create and prepare all agents
            prepared_agents = {}

            ordered_agents = OrderedDict(
                sorted(agents.items(), key=lambda x: x[1].get('collaborator_order', float('inf')))
            )
            for key, details in ordered_agents.items():
                logger.info(f"working on {key}")
                if details["activate"]:
                    print(f"Creating agent: {details['agent_name']}")
                    collaborator_agent = multi_agent_manager.create_agent(client=bedrock_agent_client,
                                                                          agent_name=details['agent_name'],
                                                                          foundation_model=foundation_model,
                                                                          role_arn=role_arn,
                                                                          instruction=details['instruction'],
                                                                          tags=details['tags'],
                                                                          agent_collaboration=(
                                                                              'SUPERVISOR' if key == "supervisor" else "DISABLED"))
                    prepared_agents[key] = {
                        'agentName': collaborator_agent['agentName'],
                        'agentArn': collaborator_agent['agentArn'],
                        'agentId': collaborator_agent['agentId'],
                        'foundationModel': collaborator_agent['foundationModel'],
                        'agentVersion': "DRAFT",
                        'tags': details['tags'],
                        'use_knowledge_base': details['use_knowledge_base'],
                        'agent_type': ('SUPERVISOR' if key == "supervisor" else "COLLABORATOR"),
                        **({'collaborator_instruction': details['collaborator_instruction'],
                            'collaborator_order': details['collaborator_order']} if key != "supervisor" else {})
                    }
                    if key != "supervisor":
                        if details['use_knowledge_base']:
                            multi_agent_manager.associate_knowledge_base_with_agent(
                                bedrock_agent_client,
                                agent_id=collaborator_agent["agentId"],
                                agent_version="DRAFT",
                                knowledge_base_id=ai_factory_knowledge_base_id,
                                description=kb_description
                            )

                        if all_action_groups_agent_functions.get(key):
                            logger.info(
                                f"Adding the group actions {all_action_groups_agent_functions.get(key)} to {collaborator_agent['agentId']}")
                            multi_agent_manager.create_agent_action_group_for_agent(client=bedrock_agent_client,
                                                                                    agent_id=collaborator_agent[
                                                                                        'agentId'],
                                                                                    agent_version="DRAFT",
                                                                                    agent_functions_configuration=
                                                                                    all_action_groups_agent_functions[
                                                                                        key])
                            prepared_agents[key]["action_groups"] = all_action_groups_agent_functions[key]

                        prepared_agent = multi_agent_manager.prepare_agent(bedrock_agent_client=bedrock_agent_client,
                                                                           agent=prepared_agents[key])

                        print(f"Details agent : {collaborator_agent}")

                        agent_alias = multi_agent_manager.create_agent_alias(bedrock_agent_client=bedrock_agent_client,
                                                                             agent_id=collaborator_agent['agentId'],
                                                                             agent_name=collaborator_agent['agentName'])
                        prepared_agents[key]["agentVersion"] = prepared_agent["agentVersion"]
                        prepared_agents[key]["agentAliasArn"] = agent_alias["agentAliasArn"]
                        prepared_agents[key]["agentAliasId"] = agent_alias["agentAliasId"]

                print(f"Prepared agents: {prepared_agents}")

            # Step 3: Associate sub-agents with the supervisor
            supervisor = prepared_agents["supervisor"]
            for key, sub_agent in prepared_agents.items():
                if key != "supervisor":
                    multi_agent_manager.associate_sub_agent_with_supervisor(bedrock_agent_client=bedrock_agent_client,
                                                                            supervisor_agent=supervisor,
                                                                            collaborator_sub_agent=sub_agent)

            # Step 4: Associate knowledge base with supervisor
            if supervisor["use_knowledge_base"]:
                multi_agent_manager.associate_knowledge_base_with_agent(
                    bedrock_agent_client=bedrock_agent_client,
                    agent_id=supervisor["agentId"],
                    agent_version=supervisor["agentVersion"],
                    knowledge_base_id=ai_factory_knowledge_base_id,
                    description=kb_description
                )
            prepared_supervisor_agent = multi_agent_manager.prepare_agent(bedrock_agent_client=bedrock_agent_client,
                                                                          agent=supervisor)
            agent_alias_id = multi_agent_manager.create_agent_alias(bedrock_agent_client=bedrock_agent_client,
                                                                    agent_id=supervisor["agentId"],
                                                                    agent_name=supervisor['agentName'])

            prepared_agents["supervisor"]["agentVersion"] = prepared_supervisor_agent["agentVersion"]
            prepared_agents["supervisor"]["agentAliasArn"] = agent_alias_id["agentAliasArn"]
            prepared_agents["supervisor"]["agentAliasId"] = agent_alias_id["agentAliasId"]
            print(f"Final prepared_agents agent : {prepared_agents}")



        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
    if mode == "delete":
        skip_agent_name = "<Agent_name_I_want_to_skip>"
        multi_agent_manager.delete_all_agents_except(bedrock_agent_client, skip_agent_name)
