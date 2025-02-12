import json

from aws_cdk.aws_iam import ServicePrincipal
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_opensearchserverless import CfnAccessPolicy
from constructs import Construct

from aws_cdk import (
    Duration,
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_ssm as ssm,
    aws_lambda_event_sources as lambda_events, RemovalPolicy, NestedStack, CustomResource, CfnOutput,
)

from aws_cdk import aws_bedrock as bedrock

from aws_cdk.aws_bedrock import CfnKnowledgeBase, CfnDataSource
from aws_cdk.aws_ecr_assets import DockerImageAsset

from reply_cdk_utils import ResourceRegistry
from reply_cdk_utils.ConventionNaming import ConventionNamingManager
from reply_cdk_utils.parameter_store import ParameterStoreManager
from reply_cdk_utils.s3 import S3Manager
from stacks.constants import SSM_KB_INPUT_BUCKET_NAME
from stacks.openss_infra_stack import OpenSearchServerlessInfraStack
from aws_cdk import custom_resources as cr
from aws_cdk.aws_iam import (
    ServicePrincipal,
)
from aws_cdk.aws_lambda import (
    Tracing,
)
from aws_cdk.aws_logs import RetentionDays, LogGroup


class KbInfraStack(NestedStack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            resource_prefix,
            envname,
            extra_configuration: dict,
            reply_ai_resource_registry: ResourceRegistry,
            oss_stack: OpenSearchServerlessInfraStack,
            embedding_model_id: str,
            chunking_strategy: str,
            max_tokens: int,
            overlap_percentage: int,
            lambda_service: DockerImageAsset,
    ) -> None:

        super().__init__(scope, construct_id)

        self.resource_prefix = resource_prefix
        self.envname = envname
        self.extra_configuration = extra_configuration
        self.resource_registry = reply_ai_resource_registry
        self.oss_stack = oss_stack
        self.index_name = oss_stack.index_name
        self.collectionArn = oss_stack.collection.attr_arn


        # Create requirements KB such as S3 bucket, KB IAM role for Bedrock
        self.__create_requirements_knowledge_base(
            resource_prefix,
            envname
        )
        # Create oss index second
        self.__create_oss_index(index_name=self.index_name,
                                embedding_model_id=embedding_model_id,
                                lambda_service=lambda_service)

        #   Create Knowledgebase
        self.knowledge_base = self.create_knowledge_base(
            resource_prefix,
            envname,
            self.index_name,
            embedding_model_id
        )
        self.knowledge_base.node.add_dependency(self.resource_registry.get_resource("INDEX_CREATION_CUSTOM_RESOURCE"))

        self.data_source = self.create_data_source(
            resource_prefix,
            envname,
            extra_configuration,
            max_tokens,
            overlap_percentage,
            self.knowledge_base,
            chunking_strategy,
        )
        self.ingest_lambda = self.create_ingest_lambda(
            self.knowledge_base,
            self.data_source,
            lambda_service
        )
        self.attr_knowledge_base_id = self.knowledge_base.attr_knowledge_base_id
        CfnOutput(self, "CfnOutputKnowledgeBaseId", value=self.attr_knowledge_base_id)
        CfnOutput(self, "CfnOutputBucketInputKB", value=self.kb_input_document_s3_bucket.bucket_name)

    def __create_requirements_knowledge_base(self,
                                             resource_prefix,
                                             envname
                                             ):

        convention_naming_kb_buckets_docs_name = ConventionNamingManager.get_s3_bucket_name_convention(
            stack=self,
            resource_prefix=resource_prefix,
            envname=envname,
            bucket_name=self.extra_configuration.get('KB_DOCS_S3_BUCKET_NAME'),
        )
        if not S3Manager.bucket_exists(convention_naming_kb_buckets_docs_name):
            kb_document_s3_bucket = self.__create_kb_bucket(
                resource_prefix,
                envname,
                self.extra_configuration.get('KB_DOCS_S3_BUCKET_NAME'))
        else:
            kb_document_s3_bucket = s3.Bucket.from_bucket_arn(
                self, "s3_bucket_arn", f"arn:aws:s3:::{convention_naming_kb_buckets_docs_name}"
            )

        self.resource_registry.add_resource("KB_DOCS_S3_BUCKET", kb_document_s3_bucket)
        self.kb_input_document_s3_bucket = kb_document_s3_bucket
        # Create KB Role
        self.kb_bedrock_role = iam.Role(
            self,
            "KB_Role",
            role_name=ConventionNamingManager.get_iam_role_name_convention(
                resource_prefix=resource_prefix,
                envname=envname,
                role_name="kb_role_ai_factory"
            ),
            assumed_by=iam.ServicePrincipal(
                "bedrock.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": self.extra_configuration.get('account_id')},
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:{self.extra_configuration.get('cdk_region')}:{self.extra_configuration.get('account_id')}:knowledge-base/*"
                    },
                },
            ),
            inline_policies={
                f"{self.resource_prefix}-{self.envname}-FoundationModelPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="BedrockInvokeModelStatementMainRegion",
                            effect=iam.Effect.ALLOW,
                            actions=["bedrock:InvokeModel"],
                            resources=[
                                f"arn:aws:bedrock:{self.extra_configuration.get('cdk_region')}::foundation-model/*"],
                        ),
                        iam.PolicyStatement(
                            sid="BedrockInvokeModelStatementSecondRegion",
                            effect=iam.Effect.ALLOW,
                            actions=["bedrock:InvokeModel"],
                            resources=[
                                f"arn:aws:bedrock:{self.extra_configuration.get('BEDROCK_REGION_NAME')}::foundation-model/*"],
                        )
                    ]
                ),
                "OSSPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="OpenSearchServerlessAPIAccessAllStatement",
                            effect=iam.Effect.ALLOW,
                            actions=["aoss:APIAccessAll"],
                            resources=[
                                f"arn:aws:aoss:{self.extra_configuration.get('cdk_region')}:{self.extra_configuration.get('account_id')}:collection/*"
                            ],
                        ),
                        iam.PolicyStatement(
                            sid="OpenSearchServerlessAPIDashboardsAccessAll",
                            effect=iam.Effect.ALLOW,
                            actions=["aoss:DashboardsAccessAll"],
                            resources=[
                                f"arn:aws:aoss:{self.extra_configuration.get('cdk_region')}:{self.extra_configuration.get('account_id')}:dashboards/*"
                            ],
                        ),
                    ]
                ),
                "S3Policy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="S3ListBucketStatement",
                            effect=iam.Effect.ALLOW,
                            actions=["s3:ListBucket"],
                            resources=[f"arn:aws:s3:::{kb_document_s3_bucket.bucket_name}"],
                        ),
                        iam.PolicyStatement(
                            sid="S3GetObjectStatement",
                            effect=iam.Effect.ALLOW,
                            actions=["s3:GetObject"],
                            resources=[f"arn:aws:s3:::{kb_document_s3_bucket.bucket_name}/*"],
                        ),
                    ]
                ),
            },
        )

        self.data_access_policy = self.create_data_access_policy(
            collection_name=self.oss_stack.collection.name,
            kb_role_arn=self.kb_bedrock_role.role_arn
        )
        # create an SSM parameters which store export values
        ssm.StringParameter(
            self,
            "kbRoleArn",
            parameter_name=ConventionNamingManager.get_ssm_name_convention(
                resource_prefix=resource_prefix,
                envname=envname,
                parameter_name="kb-role-bedrock-arn"

            ),
            string_value=self.kb_bedrock_role.role_arn,
        )

        ssm.StringParameter(
            self,
            "kbdocsbucket",
            parameter_name=ConventionNamingManager.get_ssm_name_convention(
                resource_prefix=resource_prefix,
                envname=envname,
                parameter_name=SSM_KB_INPUT_BUCKET_NAME

            ),
            string_value=kb_document_s3_bucket.bucket_name,
        )

    def create_knowledge_base(
            self,
            resource_prefix,
            envname,
            index_name,
            embedding_model_id
    ) -> CfnKnowledgeBase:

        return CfnKnowledgeBase(
            self,
            "repRagKB",
            knowledge_base_configuration=CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=f"arn:aws:bedrock:{self.extra_configuration.get('cdk_region')}::foundation-model/{embedding_model_id}"
                ),
            ),
            name=ConventionNamingManager.get_knowledge_base_name_convention(
                resource_prefix=resource_prefix,
                envname=envname,
                knowledge_base_name="kb-ai-factory"
            ),
            role_arn=self.kb_bedrock_role.role_arn,
            # the properties below are optional
            description="RAG KB for AI Factory",
            storage_configuration=CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS",
                # the properties below are optional
                opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                    collection_arn=self.collectionArn,
                    field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                        metadata_field="AMAZON_BEDROCK_METADATA",
                        text_field="AMAZON_BEDROCK_TEXT_CHUNK",
                        vector_field="bedrock-knowledge-base-default-vector",
                    ),
                    vector_index_name=index_name,
                ),
            ),
        )

    def create_data_access_policy(self, collection_name, kb_role_arn) -> CfnAccessPolicy:

        return CfnAccessPolicy(
            self,
            "DataAccessPolicy",
            name=f"{collection_name}access",
            type="data",
            policy=json.dumps(
                [
                    {
                        "Rules": [
                            {
                                "Resource": [f"collection/{collection_name}"],
                                "Permission": [
                                    "aoss:CreateCollectionItems",
                                    "aoss:UpdateCollectionItems",
                                    "aoss:DescribeCollectionItems",
                                ],
                                "ResourceType": "collection",
                            },
                            {
                                "ResourceType": "index",
                                "Resource": [f"index/{collection_name}/*"],
                                "Permission": [
                                    "aoss:CreateIndex",
                                    "aoss:DescribeIndex",
                                    "aoss:ReadDocument",
                                    "aoss:WriteDocument",
                                    "aoss:UpdateIndex",
                                    "aoss:DeleteIndex",
                                ],
                            },
                        ],
                        "Principal": [kb_role_arn],
                    }
                ]
            ),
        )

    def create_data_source(
            self,
            resource_prefix: str,
            envname: str,
            extra_configuration: dict,
            max_tokens,
            overlap_percentage,
            knowledge_base,
            chunking_strategy,
    ) -> CfnDataSource:

        kb_bucket_bedrock: s3.Bucket = self.resource_registry.get_resource("KB_DOCS_S3_BUCKET")
        kb_id = knowledge_base.attr_knowledge_base_id
        chunking_strategy = chunking_strategy
        if chunking_strategy == "Fixed-size chunking":
            vector_ingestion_config_variable = bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                    chunking_strategy="FIXED_SIZE",
                    # the properties below are optional
                    fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
                        max_tokens=max_tokens, overlap_percentage=overlap_percentage
                    ),
                )
            )
        elif chunking_strategy == "Default chunking":
            vector_ingestion_config_variable = bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                    chunking_strategy="FIXED_SIZE",
                    # the properties below are optional
                    fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
                        max_tokens=300, overlap_percentage=20
                    ),
                )
            )
        else:
            vector_ingestion_config_variable = bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                    chunking_strategy="NONE"
                )
            )
        return CfnDataSource(
            self,
            "KBDataSource",
            data_source_configuration=CfnDataSource.DataSourceConfigurationProperty(
                s3_configuration=CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=f"arn:aws:s3:::{kb_bucket_bedrock.bucket_name}",
                    inclusion_prefixes=["rag_input_document/"]
                ),
                type="S3",
            ),
            knowledge_base_id=kb_id,
            name=f"{resource_prefix}{envname}KBDataSource",
            # the properties below are optional
            description=f"Knowledge Base DataSource {self.extra_configuration.get('PROJECT_AGENT_NAME')}",
            vector_ingestion_configuration=vector_ingestion_config_variable,
            data_deletion_policy=RemovalPolicy.RETAIN.value
        )

    def create_ingest_lambda(
            self,
            knowledge_base,
            data_source,
            lambda_service
    ) -> _lambda:

        ingest_lambda = _lambda.DockerImageFunction(
            self,
            "IngestionJob",
            code=_lambda.DockerImageCode.from_ecr(
                repository=lambda_service.repository,
                tag_or_digest =lambda_service.image_tag,
                cmd=["lambdas.IngestJob.ingestJobLambda.lambda_handler"],
            ),
            timeout=Duration.minutes(5),
            environment=dict(
                KNOWLEDGE_BASE_ID=knowledge_base.attr_knowledge_base_id,
                DATA_SOURCE_ID=data_source.attr_data_source_id,
            ),
        )

        s3_put_event_source = lambda_events.S3EventSourceV2(
            self.resource_registry.get_resource("KB_DOCS_S3_BUCKET"),
            events=[s3.EventType.OBJECT_REMOVED, s3.EventType.OBJECT_CREATED_PUT],
        )
        ingest_lambda.add_event_source(s3_put_event_source)

        ingest_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:StartIngestionJob"],
                resources=[knowledge_base.attr_knowledge_base_arn],
            )
        )
        return ingest_lambda

    def __create_kb_bucket(self,
                           resource_prefix: str,
                           envname: str,
                           bucket_name: str):

        return s3.Bucket(
            self,
            id=f"knowledge_base_docs_{resource_prefix}",
            bucket_name=ConventionNamingManager.get_s3_bucket_name_convention(
                stack=self,
                resource_prefix=resource_prefix,
                envname=envname,
                bucket_name=bucket_name,
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

    def __create_oss_index(self, index_name, embedding_model_id, lambda_service):
        # dependency layer (includes requests, requests-aws4auth,opensearch-py, aws-lambda-powertools)

        oss_lambda_role = iam.Role(
            self,
            "OSSLambdaRole",
            assumed_by=ServicePrincipal("lambda.amazonaws.com"),
        )

        oss_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "aoss:APIAccessAll",
                    "aoss:List*",
                    "aoss:Get*",
                    "aoss:Create*",
                    "aoss:Update*",
                    "aoss:Delete*",
                ],
                resources=["*"],
            )
        )

        oss_index_creation_lambda = _lambda.DockerImageFunction(
            self,
            "BKB-OSS-InfraSetupLambda",
            function_name=ConventionNamingManager.get_lambda_name_convention(
                resource_prefix=self.resource_prefix,
                envname=self.envname,
                lambda_name=f"oss-index-cr-{index_name}",
            ),
            code=_lambda.DockerImageCode.from_ecr(
                repository=lambda_service.repository,
                tag_or_digest =lambda_service.image_tag,
                cmd=["lambdas.bedrock_kb_lambda.oss_handler.lambda_handler"],
            ),
            role=oss_lambda_role,
            memory_size=1024,
            timeout=Duration.minutes(14),
            tracing=Tracing.ACTIVE,
            current_version_options={"removal_policy": RemovalPolicy.DESTROY},
            environment={
                "POWERTOOLS_SERVICE_NAME": "InfraSetupLambda",
                "POWERTOOLS_METRICS_NAMESPACE": "InfraSetupLambda-NameSpace",
                "POWERTOOLS_LOG_LEVEL": "INFO",
            },
        )

        # Create a custom resource provider which wraps around the lambda above

        oss_provider_role = iam.Role(
            self,
            "OSSProviderRole",
            assumed_by=ServicePrincipal("lambda.amazonaws.com"),
        )
        oss_provider_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "aoss:APIAccessAll",
                    "aoss:List*",
                    "aoss:Get*",
                    "aoss:Create*",
                    "aoss:Update*",
                    "aoss:Delete*",
                ],
                resources=["*"],
            )
        )

        oss_index_creation_provider = cr.Provider(
            self,
            "OSSProvider",
            on_event_handler=oss_index_creation_lambda,
            log_group=LogGroup(
                self, "OSSIndexCreationProviderLogs", retention=RetentionDays.ONE_DAY
            ),
            role=oss_provider_role,
        )

        # Create a new custom resource consumer
        index_creation_custom_resource = CustomResource(
            self,
            "OSSIndexCreationCustomResource",
            service_token=oss_index_creation_provider.service_token,
            properties={
                "collection_endpoint": self.oss_stack.collection.attr_collection_endpoint,
                "data_access_policy_name": self.data_access_policy.name,
                "index_name": index_name,
                "embedding_model_id": embedding_model_id,
            },
        )

        index_creation_custom_resource.node.add_dependency(oss_index_creation_provider)
        self.resource_registry.add_resource("INDEX_CREATION_CUSTOM_RESOURCE", index_creation_custom_resource)
