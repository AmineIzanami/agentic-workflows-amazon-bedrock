from constructs import Construct

import aws_cdk as core
from aws_cdk import (
    Duration,
    Stack,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_ssm as ssm,
    aws_lambda_event_sources as lambda_events, RemovalPolicy, NestedStack,
)
from aws_cdk import custom_resources as cr
from aws_cdk.aws_iam import (
    ServicePrincipal,
)
from aws_cdk.aws_lambda import (
    Tracing,
)
from aws_cdk.aws_logs import RetentionDays, LogGroup
from aws_cdk.aws_opensearchserverless import (
    CfnAccessPolicy,
    CfnCollection,
    CfnSecurityPolicy,
)

from aws_cdk import (
    Duration,
    RemovalPolicy,
)

import json
from aws_cdk.aws_ecr_assets import DockerImageAsset

from reply_cdk_utils import ResourceRegistry
from reply_cdk_utils.ConventionNaming import ConventionNamingManager


class OpenSearchServerlessInfraStack(NestedStack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            resource_prefix: str,
            envname: str,
            reply_ai_resource_registry: ResourceRegistry,
            collection_name: str,
            index_name: str,
    ) -> None:
        super().__init__(scope, construct_id)

        self.reply_ai_resource_registry = reply_ai_resource_registry
        self.resource_prefix = resource_prefix
        self.index_name = index_name
        self.envname = envname

        # The code that defines your stack goes here
        self.encryptionPolicy = self.create_encryption_policy(collection_name)
        self.networkPolicy = self.create_network_policy(collection_name)
        self.collection = self.create_collection(collection_name)
        self.reply_ai_resource_registry.add_resource("KB_OSS_COLLECTION", self.collection)

        # Create all policies before creating the collection
        self.networkPolicy.node.add_dependency(self.encryptionPolicy)
        self.collection.node.add_dependency(self.encryptionPolicy)

        # # create an SSM parameters which store export values
        ssm.StringParameter(
            self,
            "collectionArn",
            parameter_name=ConventionNamingManager.get_ssm_name_convention(
                resource_prefix=resource_prefix,
                envname=envname,
                parameter_name="kb-oss-collection-arn-ai-factory"

            ),
            string_value=self.collection.attr_arn,
        )

        # self.create_oss_index(index_name, embedding_model_id, lambdaservice)

    def create_encryption_policy(self, collection_name) -> CfnSecurityPolicy:
        return CfnSecurityPolicy(
            self,
            "EncryptionPolicy",
            name=ConventionNamingManager.get_opensearch_collection_name_convention(
                resource_prefix=self.resource_prefix,
                envname=self.envname,
                collection_name=f"{collection_name}-enc"
            ),
            type="encryption",
            policy=json.dumps(
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{collection_name}"],
                        }
                    ],
                    "AWSOwnedKey": True,
                }
            ),
        )

    def create_network_policy(self, collection_name) -> CfnSecurityPolicy:
        return CfnSecurityPolicy(
            self,
            "NetworkPolicy",
            name=ConventionNamingManager.get_opensearch_collection_name_convention(
                resource_prefix=self.resource_prefix,
                envname=self.envname,
                collection_name=f"{collection_name}-net"
            ),
            type="network",
            policy=json.dumps(
                [
                    {
                        "Description": "Public access for ct-kb-aoss-collection collection",
                        "Rules": [
                            {
                                "ResourceType": "dashboard",
                                "Resource": [f"collection/{collection_name}"],
                            },
                            {
                                "ResourceType": "collection",
                                "Resource": [f"collection/{collection_name}"],
                            },
                        ],
                        "AllowFromPublic": True,
                    }
                ]
            ),
        )

    def create_collection(self, collection_name) -> CfnCollection:
        return CfnCollection(
            self,
            "CollectionAIFactory",
            name=collection_name,
            description=f"{collection_name}-repRAG-collection",
            type="VECTORSEARCH",
        )
