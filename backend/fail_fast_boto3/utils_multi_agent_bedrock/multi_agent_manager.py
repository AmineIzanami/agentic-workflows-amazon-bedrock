import logging
from botocore.exceptions import ClientError
import time

from botocore.exceptions import ClientError

logger = logging.getLogger()


def delete_all_agents_except(client, exclude_agent_name):
    """
    Deletes all Bedrock agents except the one with the specified agent_name.
    First deletes all aliases associated with each agent before deleting the agent itself.
    """
    try:
        response = client.list_agents()
        agents = response.get('agentSummaries', [])
        if not agents:
            print("No agents found to delete.")
            return

        for agent in agents:
            if agent['agentName'] != exclude_agent_name:
                agent_id = agent['agentId']
                try:
                    # First, list all aliases for this agent
                    aliases_response = client.list_agent_aliases(agentId=agent_id)
                    aliases = aliases_response.get('agentAliasSummaries', [])

                    # Delete each alias
                    for alias in aliases:
                        alias_id = alias['agentAliasId']
                        try:
                            client.delete_agent_alias(agentId=agent_id, agentAliasId=alias_id)
                            print(f"Deleted alias {alias_id} for agent: {agent['agentName']}")
                        except ClientError as e:
                            print(f"Failed to delete alias {alias_id} for agent {agent['agentName']}: {e}")

                    # After all aliases are deleted, delete the agent
                    client.delete_agent(agentId=agent_id)
                    print(f"Deleted agent: {agent['agentName']} (ID: {agent_id})")
                except ClientError as e:
                    print(f"Failed to delete agent {agent['agentName']} (ID: {agent_id}): {e}")
            else:
                print(f"Skipping deletion of agent: {agent['agentName']} (ID: {agent['agentId']})")
    except ClientError as e:
        logging.error(f"Error listing or deleting agents: {e}")
        raise


def disassociate_all_agents_from_supervisor(client,agent_supervisor):
    """
    Deletes all Bedrock agents except the one with the specified agent_name.
    First deletes all aliases associated with each agent before deleting the agent itself.
    """
    try:
        response = client.list_agent_collaborators(
            agentId=agent_supervisor['agentId'],
            agentVersion=agent_supervisor["agentVersion"],
        )
        _all_associations = response["agentCollaboratorSummaries"]
        for _collaborator_agent in _all_associations:
            response = client.disassociate_agent_collaborator(
                agentId=_collaborator_agent['agentId'],
                agentVersion=_collaborator_agent['agentVersion'],
                collaborationId=_collaborator_agent['collaborationId']
            )
            print(f"Disassociated agent {_collaborator_agent['agentName']} from supervisor")
    except ClientError as e:
        logging.error(f"Error listing or deleting agents: {e}")
        raise


def get_existing_agent(client, agent_name):
    """
    Checks if an agent with the given agent_name already exists.
    """
    try:
        response = client.list_agents()
        for agent in response.get('agentSummaries', []):
            if agent['agentName'] == agent_name:
                response = client.get_agent(
                    agentId=agent['agentId']
                )
                return response['agent']
    except ClientError as e:
        logging.error(f"Error checking existing agents: {e}")
        raise
    return None


def create_agent_alias(bedrock_agent_client, agent_id, agent_name):
    """
    Creates an alias for a given agent.

    Args:
        bedrock_agent_client: Bedrock client
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


def create_agent(*,client,agent_name, foundation_model, role_arn, instruction, tags, agent_collaboration="DISABLED"):
    """
    Creates a Bedrock agent with the specified parameters.
    """
    existing_agent = get_existing_agent(client, agent_name)
    if existing_agent:
        print(f"Agent '{agent_name}' already exists. Skipping creation. Details : {existing_agent}")
        return existing_agent

    try:

        response = client.create_agent(
            agentName=agent_name,
            foundationModel=foundation_model,
            agentResourceRoleArn=role_arn,
            instruction=instruction,
            tags=tags,
            agentCollaboration=agent_collaboration,
            idleSessionTTLInSeconds=3600
        )
        agent_status = client.get_agent(agentId=response['agent']['agentId'])
        while agent_status["agent"]["agentStatus"] == "CREATING":
            time.sleep(0.5)
            agent_status = client.get_agent(agentId=response['agent']['agentId'])

        return response['agent']
    except ClientError as e:
        logging.error(f"Error creating agent {agent_name}: {e}")
        raise


def prepare_agent(bedrock_agent_client, agent):
    """
    Prepares an agent and retrieves its version.
    """
    # Prepare the Agent
    agent_id = agent['agentId']
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
        f"Prepared agent '{agent['agentName']}' with version: {preparation_response['agentVersion']} : Status {agent_prep_status} : response {response['agent']}")
    return preparation_response


def update_agent_to_supervisor(client, prepared_supervisor_agent):
    """
    Updates an agent to set its collaboration mode to SUPERVISOR.
    """
    try:
        agent_id = prepared_supervisor_agent["agentId"]
        print(f"Updating agent ID '{agent_id}' to SUPERVISOR...")
        client.update_agent(agentId=prepared_supervisor_agent["agentId"],
                            agentName=prepared_supervisor_agent["agentName"],
                            agentResourceRoleArn=prepared_supervisor_agent["agentArn"],
                            foundationModel=prepared_supervisor_agent["foundationModel"],
                            agentCollaboration="SUPERVISOR")
        print(f"Updated agent '{agent_id}' to SUPERVISOR.")
    except ClientError as e:
        logging.error(f"Error updating agent ID '{agent_id}' to SUPERVISOR: {e}")
        raise


def associate_sub_agent_with_supervisor(bedrock_agent_client, supervisor_agent, collaborator_sub_agent):
    """
    Associates a sub-agent with the supervisor using the `associate_agent_collaborator` API.
    """
    try:
        print(f"Associating {collaborator_sub_agent} to {supervisor_agent['agentId']} ")
        bedrock_agent_client.associate_agent_collaborator(
            agentDescriptor={'aliasArn': collaborator_sub_agent["agentAliasArn"]},
            agentId=supervisor_agent['agentId'],
            agentVersion=supervisor_agent['agentVersion'],
            collaborationInstruction=collaborator_sub_agent['collaborator_instruction'],
            collaboratorName=collaborator_sub_agent['agentName'],
            relayConversationHistory='TO_COLLABORATOR'
        )
        print(
            f"Associated sub-agent '{collaborator_sub_agent['agentName']}' with supervisor '{supervisor_agent['agentName']}'.")
    except bedrock_agent_client.exceptions.ConflictException as e:
        logging.warning(
            f"AssociateAgentCollaborator  already associated with Agent ID {supervisor_agent['agentId']}. Skipping association."
        )
    except ClientError as e:
        logging.error(
            f"Error associating sub-agent '{collaborator_sub_agent['agentName']}' with supervisor '{supervisor_agent['agentName']}': {e}")
        raise


def create_agent_action_group_for_agent(*, client, agent_id, agent_version, agent_functions_configuration):
    for _action_group in agent_functions_configuration:
        agent_action_group_response = client.create_agent_action_group(
            agentId=agent_id,
            agentVersion=agent_version,
            actionGroupExecutor={
                'lambda': _action_group["function_arn"]
            },
            actionGroupName=_action_group["agent_action_group_name"],
            functionSchema={
                'functions': _action_group["agent_functions"]
            },
            description=_action_group["agent_action_description"]
        )


def associate_knowledge_base_with_agent(bedrock_agent_client, agent_id, agent_version, knowledge_base_id, description):
    """
    Associates a knowledge base with an agent using the `associate_agent_knowledge_base` API.
    """
    try:
        bedrock_agent_client.associate_agent_knowledge_base(
            agentId=agent_id,
            agentVersion=agent_version,
            knowledgeBaseId=knowledge_base_id,
            description=description
        )
        print(f"Knowledge Base '{knowledge_base_id}' associated with Agent ID '{agent_id}', Version '{agent_version}'.")
    except bedrock_agent_client.exceptions.ConflictException as e:
        logging.warning(
            f"Knowledge Base '{knowledge_base_id}' is already associated with Agent ID '{agent_id}'. Skipping association."
        )
    except ClientError as e:
        logging.error(f"Error associating Knowledge Base '{knowledge_base_id}' with Agent ID '{agent_id}': {e}")
        raise


# Function to read XML content
def read_xml_content(file_path):
    with open(file_path, "r") as file:
        return file.read().strip()
