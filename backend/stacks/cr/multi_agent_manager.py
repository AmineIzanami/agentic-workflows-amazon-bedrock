import logging
import time
from typing import Dict

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Bedrock Client
bedrock_agent_client = boto3.client('bedrock-agent')


def delete_all_agents_in_list(list_agent_name):
    """
    Deletes all Bedrock agents except the one with the specified agent_name.
    First deletes all aliases associated with each agent before deleting the agent itself.
    """
    try:
        response = bedrock_agent_client.list_agents()
        agents = response.get('agentSummaries', [])
        if not agents:
            print("No agents found to delete.")
            return

        for agent in agents:
            if agent['agentName'] in list_agent_name:
                agent_id = agent['agentId']
                try:
                    # First, list all aliases for this agent
                    aliases_response = bedrock_agent_client.list_agent_aliases(agentId=agent_id)
                    aliases = aliases_response.get('agentAliasSummaries', [])

                    # Delete each alias
                    for alias in aliases:
                        alias_id = alias['agentAliasId']
                        try:
                            bedrock_agent_client.delete_agent_alias(agentId=agent_id, agentAliasId=alias_id)
                            print(f"Deleted alias {alias_id} for agent: {agent['agentName']}")
                        except ClientError as e:
                            print(f"Failed to delete alias {alias_id} for agent {agent['agentName']}: {e}")
                    time.sleep(1)
                    # After all aliases are deleted, delete the agent
                    bedrock_agent_client.delete_agent(agentId=agent_id)
                    print(f"Deleted agent: {agent['agentName']} (ID: {agent_id})")
                except ClientError as e:
                    print(f"Failed to delete agent {agent['agentName']} (ID: {agent_id}): {e}")
            else:
                print(f"Skipping deletion of agent: {agent['agentName']} (ID: {agent['agentId']})")
    except ClientError as e:
        logging.error(f"Error listing or deleting agents: {e}")
        raise


def get_latest_agent_version(agent_id) -> Dict:
    """
    Fetches the latest version alias of an AWS Bedrock Agent with exponential backoff.

    Parameters:
        agent_id (str): The ID of the Bedrock agent.
    Returns:
        str: Latest version alias if found.

    Raises:
        RuntimeError: If no version is found after max_retries.
    """
    # Initial backoff interval in seconds
    BACKOFF_INTERVAL = 5
    # Maximum backoff interval
    MAX_BACKOFF = 60
    # Maximum number of retries
    MAX_RETRIES = 10

    for attempt in range(MAX_RETRIES):
        try:
            response = bedrock_agent_client.list_agent_aliases(
                agentId=agent_id,
            )
            # Check if we got any versions
            if response.get('agentAliasSummaries'):
                latest_alias_version = response['agentAliasSummaries'][0]
                latest_alias_status = latest_alias_version.get('agentAliasStatus')
                print(f"Latest Version Alias: {latest_alias_version}")
                if latest_alias_status in ["PREPARED"]:
                    response_alias = bedrock_agent_client.get_agent_alias(
                        agentAliasId=latest_alias_version.get('agentAliasId'),
                        agentId=agent_id
                    )
                    print(f"Details agents {response_alias['agentAlias']}")
                    return response_alias["agentAlias"]

            print(f"Attempt {attempt + 1}: No versions found. Retrying...")

        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {str(e)}")

        # Exponential backoff with jitter to avoid collision
        time.sleep(BACKOFF_INTERVAL)  # nosem: arbitrary-sleep
        BACKOFF_INTERVAL = min(
            MAX_BACKOFF, BACKOFF_INTERVAL * 2
        )  # Exponential backoff with a maximum limit

    raise RuntimeError(
        f"Exceeded max retries. No version found for the given agent. The Agent {agent_id} has not been prepared")


def associate_sub_agents(supervisor_agent_id, supervisor_agent_version, agents):
    """
    Associates sub-agents with the supervisor.
    """
    logger.info(
        f"Associating {len(agents)} sub-agents with Supervisor ID: {supervisor_agent_id} with version {supervisor_agent_version}")
    logger.info(f"Details Sub Agent {agents}")
    for _sub_agent in agents:
        if _sub_agent.get("to_collaborate") == "true":
            try:
                _alias_agent_details = get_latest_agent_version(_sub_agent["agentId"])

                response = bedrock_agent_client.associate_agent_collaborator(
                    agentDescriptor={"aliasArn": _alias_agent_details["agentAliasArn"]},
                    agentId=supervisor_agent_id,
                    agentVersion=supervisor_agent_version,
                    collaborationInstruction=_sub_agent["collaborator_instruction"],
                    collaboratorName=_sub_agent["agentName"],
                    relayConversationHistory="TO_COLLABORATOR"
                )

                # validate response is 200 in httpstatuscode
                if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
                    raise Exception(f"Error associating sub-agent {_sub_agent['agentName']}: {response}")
                logger.info(f"Successfully associated {_sub_agent['agentName']} with Supervisor")
            except bedrock_agent_client.exceptions.ConflictException as e:
                logging.warning(
                    f"AssociateAgentCollaborator {_alias_agent_details['agentAliasArn']} already associated with Agent ID {supervisor_agent_id}. Skipping association."
                )
            except Exception as e:
                logger.error(f"Error associating sub-agent {_sub_agent['agentName']}: {e}")


def associate_knowledge_base_with_agent(supervisor_agent_id, supervisor_agent_version, knowledge_base_id,
                                        description="Knowledge base for supervisor agent"):
    """
    Associates a knowledge base with an agent using the `associate_agent_knowledge_base` API.
    """
    try:
        bedrock_agent_client.associate_agent_knowledge_base(
            agentId=supervisor_agent_id,
            agentVersion=supervisor_agent_version,
            knowledgeBaseId=knowledge_base_id,
            description=description
        )
        print(
            f"Knowledge Base '{knowledge_base_id}' associated with Agent ID '{supervisor_agent_id}', Version '{supervisor_agent_version}'.")
    except bedrock_agent_client.exceptions.ConflictException as e:
        logging.warning(
            f"Knowledge Base '{knowledge_base_id}' is already associated with Agent ID '{supervisor_agent_id}'. Skipping association."
        )
    except ClientError as e:
        logging.error(
            f"Error associating Knowledge Base '{knowledge_base_id}' with Agent ID '{supervisor_agent_id}': {e}")
        raise


def create_agent_alias(agent_id, agent_name):
    """
    Creates an alias for a given agent.

    Args:
        agent_id: ID of the agent
        agent_name: Name of the agent to use in alias creation

    Returns:
        The created alias ID if successful, None if failed
    """
    try:
        # Initial backoff interval in seconds
        BACKOFF_INTERVAL = 5
        # Maximum backoff interval
        MAX_BACKOFF = 60
        # Maximum number of retries
        MAX_RETRIES = 10

        # Create an alias agent_name using the agent agent_name and current timestamp
        agent_alias_name = f"{agent_name}-alias-{int(time.time())}"

        create_agent_response = bedrock_agent_client.create_agent_alias(
            agentId=agent_id,
            agentAliasName=agent_alias_name,
            description=f"Agent description for {agent_alias_name}",  # A description of the alias of the agent.
        )

        # Check the create agent alias status in a loop
        for attempt in range(MAX_RETRIES):
            response = bedrock_agent_client.get_agent_alias(
                agentId=create_agent_response['agentAlias']['agentId'],
                agentAliasId=create_agent_response['agentAlias']['agentAliasId']
            )
            alias_state = response["agentAlias"]["agentAliasStatus"]

            if alias_state == "PREPARED":
                logger.info(
                    f"The Bedrock Agent {agent_id} Alias {agent_alias_name} created successfully."
                )
                break
            elif alias_state in ["CREATING", "UPDATING"]:
                logger.info(
                    f"The Bedrock Agent {agent_id} Alias {agent_alias_name} is currently {alias_state.lower()}. Waiting..."
                )
                # nosemgrep: <arbitrary-sleep Message: time.sleep() call>
                time.sleep(BACKOFF_INTERVAL)  # nosem: arbitrary-sleep
                BACKOFF_INTERVAL = min(
                    MAX_BACKOFF, BACKOFF_INTERVAL * 2
                )  # Exponential backoff with a maximum limit
            else:
                logger.info(
                    f"Unexpected state for create_agent_alias {agent_alias_name}: {alias_state}"
                )
                break
        return create_agent_response["agentAlias"]
    except ClientError as e:
        print(f"Error creating alias for agent {agent_name}: {e}")
        return None


def prepare_agent(supervisor_agent_id):
    """
    Prepares an agent and retrieves its version.
    """
    # Prepare the Agent
    agent_id = supervisor_agent_id
    preparation_response = bedrock_agent_client.prepare_agent(agentId=agent_id)

    # Initial backoff interval in seconds
    backoff_interval = 5
    # Maximum backoff interval
    max_backoff = 60
    # Maximum number of retries
    max_retries = 10

    # Check agent status
    for attempt in range(max_retries):
        # Get the alias creating status.
        response = bedrock_agent_client.get_agent(agentId=agent_id)
        agent_prep_status = response["agent"]["agentStatus"]
        agent_name = response["agent"]["agentName"]

        if (
                agent_prep_status == "PREPARED"
        ):  # 'CREATING'|'PREPARED'|'FAILED'|'UPDATING'|'DELETING'
            logger.info(f"The Bedrock Agent {agent_id} is prepared successfully.")
            break
        elif agent_prep_status in ["CREATING", "UPDATING", "PREPARING"]:
            logger.info(
                f"The Bedrock Agent {agent_id} is currently {agent_prep_status.lower()}. Waiting..."
            )
            # nosemgrep: <arbitrary-sleep Message: time.sleep() call>
            time.sleep(backoff_interval)  # nosem: arbitrary-sleep
            backoff_interval = min(
                max_backoff, backoff_interval * 2
            )  # Exponential backoff with a maximum limit

        else:
            # Handle unexpected alias create state
            logger.info(
                f"Unexpected state for the agent {agent_id}: {agent_prep_status}"
            )
            break

    print(
        f"Prepared agent '{agent_name}' with version: {preparation_response['agentVersion']} : Status {agent_prep_status} : response {response['agent']}")
    return preparation_response
