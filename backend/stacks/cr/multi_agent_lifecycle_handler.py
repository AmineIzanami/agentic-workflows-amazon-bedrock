import logging
import traceback

import boto3

import cfnresponse
from multi_agent_manager import create_agent_alias, associate_sub_agents, associate_knowledge_base_with_agent, \
    prepare_agent, delete_all_agents_in_list

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Bedrock Client
bedrock_agent_client = boto3.client('bedrock-agent')


#######€xample payload###########
# {
#                 "SupervisorAgentName": self.sow_agents["supervisor"].agent_name,
#                 "SupervisorAgentResourceRoleArn": self.sow_agents["supervisor"].agent_resource_role_arn,
#                 "SupervisorAgentVersion": self.sow_agents["supervisor"].agent_version,
#                 "SupervisorInstruction": self.sow_agents["supervisor"].instruction,
#                 "SupervisorDescription": self.sow_agents["supervisor"].collaborator_instruction,
#                 "SupervisorFoundationModel": self.sow_agents["supervisor"].foundation_model,
#                 "SupervisorTags": self.extra_configuration.get("tags"),
#                 "Agents": [
#                     {
#                         "agentId": agent.get("agent_id"),
#                         "collaborator_instruction": agent.get("collaborator_instruction"),
#                         "agentName": agent.get("agent_name")
#                     }
#                     # for key, agent in self.sow_agents.items() if (not agent.supervisor) and agent.activate
#                     for key, agent in _dict_agents_config.items() if
#                     (not agent.get("supervisor")) and agent.get("activate")
#
#                 ]
#             }
#####################

def lambda_handler(event, context):
    print(f'Version boto3 : {boto3.__version__}') #to validate the Agent runtime is within the boto3 version
    """
    Lambda function to manage Supervisor Agent associations in AWS Bedrock.
    """
    logger.info(f"Received event: {event}")

    request_type = event["RequestType"]

    try:
        # Get agent configuration from event properties
        agent_config = event["ResourceProperties"]
        response_data = {}
        supervisor_agent_name = agent_config["SupervisorAgentName"]
        supervisor_agent_id = agent_config["SupervisorAgentId"]
        supervisor_agent_version = agent_config["SupervisorAgentVersion"]

        agents = agent_config["Agents"]  # List of sub-agents

        if request_type == "Create" or request_type == "Update":
            # Step 1: Associate Sub-Agents with Supervisor
            for _sub_agents in agents:
                agent_alias = create_agent_alias(agent_id=_sub_agents['agentId'],
                                                 agent_name=_sub_agents['agentName'])

                _sub_agents["agentAliasArn"] = agent_alias["agentAliasArn"]
                _sub_agents["agentAliasId"] = agent_alias["agentAliasId"]

            print(f"New agents enriched {agents}")

            associate_sub_agents(supervisor_agent_id=supervisor_agent_id,
                                 supervisor_agent_version=supervisor_agent_version,
                                 agents=agents)

            # Step 2: Associate Knowledge Base
            if "KnowledgeBaseId" in agent_config:
                knowledge_base_id = agent_config["KnowledgeBaseId"]
                associate_knowledge_base_with_agent(supervisor_agent_id=supervisor_agent_id,
                                                    supervisor_agent_version=supervisor_agent_version,
                                                    knowledge_base_id=knowledge_base_id)

            # Step 3: Prepare Supervisor Agent
            preparation_response = prepare_agent(supervisor_agent_id)

            # Step 4: Create Agent Alias
            agent_alias = create_agent_alias(agent_id=supervisor_agent_id,
                                             agent_name=supervisor_agent_name)
            response_data = {
                "Status": "Success",
                "SupervisorAgentId": preparation_response["agentId"],
                "SupervisorAgentAliasArn": agent_alias["agentAliasArn"]
            }
        elif request_type == "Delete":
            _list_agents_to_delete = [agent["agentName"] for agent in agents]
            delete_all_agents_in_list(_list_agents_to_delete)
            logger.info("Collaborators Deleted")
            delete_all_agents_in_list([supervisor_agent_name])
            logger.info("Supervisor Deleted")
            response_data = {
                "Status": "Success"
            }
        cfnresponse.send(event,
                         context,
                         cfnresponse.SUCCESS,
                         responseData={"Data": response_data},
                         physicalResourceId="CRMultiAgentLifecyclePhysicalID")

    except Exception as e:
        logger.error(f"Error in processing: {str(e)}")
        traceback.print_exc()
        cfnresponse.send(event, context, cfnresponse.FAILED, {"Error": str(e)}, "CRMultiAgentLifecyclePhysicalID")
