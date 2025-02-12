from dataclasses import asdict

from aws_cdk import (
    aws_iam as iam,
    Duration,
    aws_lambda as _lambda,
    aws_ec2 as ec2,
    CustomResource,
    custom_resources as cr,
    aws_s3 as s3,
    aws_bedrock as bedrock, Stack, RemovalPolicy, CfnOutput
)
from aws_cdk.aws_bedrock import CfnAgent
from constructs import Construct

from reply_cdk_utils.ConventionNaming import ConventionNamingManager
from reply_cdk_utils.iam import IamManager
from stacks import Reply_Agent
from stacks.agent_loader import AgentLoader


class StandaloneGenAiLayer(Stack):
    def __init__(
            self,
            scope: Construct,
            id: str,
            resource_prefix: str,
            envname: str,
            vpc_id: str,
            prod_sizing: bool,
            bedrock_engine_region: str,
            extra_configuration: dict,
            **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.resource_prefix = resource_prefix
        self.envname = envname
        self.bedrock_engine_region = bedrock_engine_region
        self.extra_configuration = extra_configuration
        MULTI_AGENT_TOOLS_TIMEOUT = 300
        ai_factory_vpc = ec2.Vpc.from_lookup(
            self,
            "AiFactoryNoKBExistingVpc",
            vpc_id=vpc_id
        )
        self.sow_check_tools = _lambda.DockerImageFunction(
            self,
            f"HandleSoWRetrievalHandler{resource_prefix}",
            function_name=ConventionNamingManager.get_lambda_name_convention(
                resource_prefix=resource_prefix,
                envname=envname,
                lambda_name="agent-tool-sow-reader",
            ),
            description="Lambda responsible of handling the retrieval of the statement of work from the S3",
            role=IamManager.create_function_role(
                self,
                envname=envname,
                resource_prefix=resource_prefix,
                fn_name="analyse-sow",
            ),
            code=_lambda.DockerImageCode.from_image_asset(
                directory="code/services/lambdas/multi_agent_handlers",
                cmd=["agent_tools.sow_reader.lambda_handler"],
            ),
            vpc=ai_factory_vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            memory_size=512 if prod_sizing else 256,
            timeout=Duration.seconds(MULTI_AGENT_TOOLS_TIMEOUT),
            environment={
                "ENVNAME": envname,
                "LOG_LEVEL": "INFO",
                "AI_FACTORY_REGION_NAME": self.region,
                "BEDROCK_REGION_NAME": self.bedrock_engine_region,
                "LLM_MODEL_AGENT": extra_configuration.get("AGENT_FOUNDATION_MODEL"),
                "ANALYSE_AWS_DIAGRAM_AGENT_PROMPT": """
                    Describe this image Return the type and describe what it has as details
                    Identify any missing or misconfigured components.
                    Provide a list of potential improvements or modifications to enhance.
                    """
            },
            tracing=_lambda.Tracing.ACTIVE,
        )
        self.sow_check_tools.add_permission(
            f"{resource_prefix}USBedrockAccess",
            action="lambda:InvokeFunction",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            source_arn=f"arn:aws:bedrock:{self.bedrock_engine_region}:{self.account}:agent/*",
        )
        self.sow_check_tools.add_permission(
            f"{resource_prefix}EUBedrockAccess",
            action="lambda:InvokeFunction",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            source_arn=f"arn:aws:bedrock:{self.region}:{self.account}:agent/*",
        )

        ### Create S3 Bucket to upload documents to when interacting with the agents by passing an S3 URI for the get_document_s3 function
        ## this is not a knowledge base, it has only a demo Purpose (a dummy)
        dummy_s3_bucket = s3.Bucket(
            self,
            id=f"buffer_bucket_{resource_prefix}",
            bucket_name=ConventionNamingManager.get_s3_bucket_name_convention(
                stack=self,
                resource_prefix=resource_prefix,
                envname=envname,
                bucket_name="dummy-demo",
            ),
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=False,
            auto_delete_objects=True if envname == "dev" else False,
            removal_policy=(
                RemovalPolicy.DESTROY if envname == "dev" else RemovalPolicy.RETAIN
            ),
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    expiration=Duration.days(365),
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30),
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90),
                        ),
                    ],
                )
            ],
        )
        CfnOutput(self, "S3BucketDummy", value=dummy_s3_bucket.bucket_name)

        agent_get_s3_file = CfnAgent.AgentActionGroupProperty(
            action_group_name="lambda_processing_sow",
            action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                lambda_=self.sow_check_tools.function_arn
            ),
            action_group_state="ENABLED",
            description="Responsible of calling the lambda function to download the S3 uri and return the content of the files ",
            function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                functions=[bedrock.CfnAgent.FunctionProperty(
                    name='get_document_from_s3',
                    description='the S3 uri to use to download the Statement of work from S3',
                    parameters={
                        "s3_uri_path": bedrock.CfnAgent.ParameterDetailProperty(
                            type="string",
                            description="the S3 uri of the document",
                            required=True
                        )
                    },
                    require_confirmation="DISABLED"
                )]
            )
        )

        agent_analyse_image_in_document = CfnAgent.AgentActionGroupProperty(
            action_group_name="lambda_processing_sow",
            action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                lambda_=self.sow_check_tools.function_arn
            ),
            action_group_state="ENABLED",
            description="Responsible of calling the lambda function to analyse the images in the PDF and get extra details to pass to the other agents ",
            function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                functions=[bedrock.CfnAgent.FunctionProperty(
                    name='analyse_images_documents',
                    description='the S3 uri to use to download the document from S3 and get the description of the images within the documents',
                    parameters={
                        "s3_uri_path": bedrock.CfnAgent.ParameterDetailProperty(
                            type="string",
                            description="the S3 uri of the original document",
                            required=True
                        )
                    },
                    require_confirmation="DISABLED"
                )]
            )
        )
        agent_available_tools = {
            "agent_get_s3_file": agent_get_s3_file,
            "agent_analyse_image_in_document": agent_analyse_image_in_document
        }

        agent_resource_role = self.create_agent_execution_role()

        agent_loader = AgentLoader("stacks/configuration/agent_config.yaml")
        self.sow_agents = agent_loader.load_agents(
            agent_resource_role=agent_resource_role,
            agent_available_tools=agent_available_tools
        )

        cr_agent_resource_role = iam.Role(
            self,
            "CRChatBotBedrockAgentRole",
            role_name=f"{self.resource_prefix}-{self.envname}-crbedrockagents",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        for _agent_key, _agent_configuration in self.sow_agents.items():
            if not _agent_configuration.supervisor and _agent_configuration.activate:
                cfn_agent = bedrock.CfnAgent(self, _agent_key,
                                             agent_name=_agent_configuration.agent_name,
                                             action_groups=_agent_configuration.agent_action_group,
                                             agent_resource_role_arn=_agent_configuration.agent_resource_role_arn,
                                             auto_prepare=True,
                                             description=_agent_configuration.collaborator_instruction,
                                             foundation_model=_agent_configuration.foundation_model,
                                             idle_session_ttl_in_seconds=240,
                                             instruction=_agent_configuration.instruction,
                                             skip_resource_in_use_check_on_delete=False if envname == "prod" else True,
                                             )

                _agent_configuration.agent_id = cfn_agent.attr_agent_id

        supervisor_cr = self.create_supervisor_agent(custom_resource_role=cr_agent_resource_role,
                                                     supervisor_agent_config=self.sow_agents.get("supervisor"))
        self.sow_agents.get("supervisor").agent_id = supervisor_cr.get_response_field("agent.agentId")

        cr_supervisor_handler = self.multi_agent_lifecycle_agent_custom_resource()

    def multi_agent_lifecycle_agent_custom_resource(self):
        cr_lambda_role = iam.Role(
            self,
            "CRLifecyleAgentLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess"),
            ],
        )

        cr_multi_agent_manager = _lambda.DockerImageFunction(
            self,
            f"{self.resource_prefix}CRMultiAgentLifecycleLambda",
            function_name=ConventionNamingManager.get_lambda_name_convention(
                resource_prefix=self.resource_prefix,
                envname=self.envname,
                lambda_name="cr-manage-agents-lifecycle",
            ),
            description="Lambda responsible of handling multi agents lifecycles",
            role=cr_lambda_role,
            code=_lambda.DockerImageCode.from_image_asset(
                directory="stacks/cr",
                cmd=["multi_agent_lifecycle_handler.lambda_handler"],
            ),
            memory_size=256,
            timeout=Duration.seconds(240),
        )

        _dict_agents_config = {
            key: asdict(agent) for key, agent in self.sow_agents.items()
        }

        # Create a Custom Resource Provider
        provider = cr.Provider(
            self,
            "MultiAgentLifecycleAgentProvider",
            on_event_handler=cr_multi_agent_manager,
        )

        # Create the Custom Resource
        cr_associate_prepare_supervisor = CustomResource(
            self,
            "MultiAgentLifecycleCR",
            service_token=provider.service_token,
            properties={
                "SupervisorAgentName": self.sow_agents["supervisor"].agent_name,
                "SupervisorAgentId": self.sow_agents["supervisor"].agent_id,
                "SupervisorAgentResourceRoleArn": self.sow_agents["supervisor"].agent_resource_role_arn,
                "SupervisorAgentVersion": self.sow_agents["supervisor"].agent_version,
                "SupervisorInstruction": self.sow_agents["supervisor"].instruction,
                "SupervisorDescription": self.sow_agents["supervisor"].collaborator_instruction,
                "SupervisorFoundationModel": self.sow_agents["supervisor"].foundation_model,
                "SupervisorTags": self.extra_configuration.get("tags"),
                "Agents": [
                    {
                        "agentId": agent.get("agent_id"),
                        "collaborator_instruction": agent.get("collaborator_instruction"),
                        "agentName": agent.get("agent_name"),
                        "to_collaborate": agent.get("to_collaborate")
                    }
                    for key, agent in _dict_agents_config.items() if
                    (not agent.get("supervisor")) and agent.get("activate")

                ]
            },
        )

        return cr_associate_prepare_supervisor

    def create_supervisor_agent(self, custom_resource_role: iam.Role, supervisor_agent_config: Reply_Agent):
        supervisor_cr = cr.AwsCustomResource(
            self,
            "SupervisorAgentCustomResource",
            function_name=ConventionNamingManager.get_lambda_name_convention(
                resource_prefix=self.resource_prefix,
                envname=self.envname,
                lambda_name="cr-create-supervisor",
            ),
            resource_type="Custom::BedrockCreateSupervisorAgent",
            install_latest_aws_sdk=True,
            on_create=cr.AwsSdkCall(
                service="bedrock-agent",
                action="createAgent",
                parameters={
                    "agentName": supervisor_agent_config.agent_name,
                    "agentResourceRoleArn": supervisor_agent_config.agent_resource_role_arn,
                    "foundationModel": supervisor_agent_config.foundation_model,
                    "description": supervisor_agent_config.agent_description,
                    "instruction": supervisor_agent_config.instruction,
                    "idleSessionTTLInSeconds": 1800,
                    "agentCollaboration": "SUPERVISOR",  # Enable Supervisor Mode
                    "orchestrationType": "DEFAULT",
                    "tags": self.extra_configuration.get("tags")
                },
                physical_resource_id=cr.PhysicalResourceId.of("SupervisorAgentCustomResource"),
            ),
            on_update=cr.AwsSdkCall(
                service="bedrock-agent",
                action="updateAgent",
                parameters={
                    "agentId": cr.PhysicalResourceId.from_response("agent.agentId"),
                    "agentName": supervisor_agent_config.agent_name,
                    "foundationModel": supervisor_agent_config.foundation_model,
                    "agentResourceRoleArn": supervisor_agent_config.agent_resource_role_arn,
                    "instruction": supervisor_agent_config.instruction,
                    "idleSessionTTLInSeconds": 1800,
                },
                physical_resource_id=cr.PhysicalResourceId.of("SupervisorAgentCustomResource"),
            ),
            role=custom_resource_role,
        )
        supervisor_cr.grant_principal.add_to_principal_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:CreateAgent",
                "bedrock:DeleteAgent",
                "bedrock:UpdateAgent",
                "bedrock:TagResource",
                "bedrock:CreateAgent"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}:{self.account}:agent/*",
                f"arn:aws:bedrock:{self.region}:{self.account}:agent-alias/*"
            ],
        )
        )
        supervisor_cr.grant_principal.add_to_principal_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "iam:CreateServiceLinkedRole",
                "iam:PassRole"
            ],
            resources=[
                "*"
            ],
        )
        )
        return supervisor_cr

    def create_agent_execution_role(self):
        agent_resource_role = iam.Role(
            self,
            "MultiAgentBedrockAgentRole",
            role_name=f"{self.resource_prefix}-{self.envname}-AmazonBedrockExecutionRoleForAgents",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:*"],
                resources=[
                    "*"
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceAccount": f"{self.account}",
                    },
                },

            ),
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucketVersions",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                    "s3:GetObjectVersion",
                    "logs:StartQuery",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams",
                ],
                resources=[
                    f"arn:aws:s3:::{self.resource_prefix}-{self.envname}-{self.account}-{self.region}-*/*",
                    f"arn:aws:s3:::{self.resource_prefix}-{self.envname}-{self.account}-{self.region}-*",
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:*{self.resource_prefix}*:log-stream:*",
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:*{self.resource_prefix}*",
                ],
            ),
        ]

        for statement in policy_statements:
            agent_resource_role.add_to_policy(statement)

        return agent_resource_role
