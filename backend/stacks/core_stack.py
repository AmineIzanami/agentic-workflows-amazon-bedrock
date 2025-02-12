from aws_cdk import (
    # Duration,
    aws_ec2 as ec2,
    Stack, )
from constructs import Construct

from reply_cdk_utils import ResourceRegistry
from stacks.genai_layer import GenAiLayer
from stacks.kb_infra_stack import KbInfraStack
from stacks.lambdas_stack import LambdaImagesStack
from stacks.openss_infra_stack import OpenSearchServerlessInfraStack


class CoreStack(Stack):
    def __init__(
            self,
            scope: Construct,
            id: str,
            resource_prefix: str,
            envname: str,
            vpc_id: str,
            extra_configuration: dict,
            **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        reply_ai_resource_registry = ResourceRegistry()

        # Import the existing VPC using its ID
        ai_factory_existing_vpc = ec2.Vpc.from_lookup(
            self,
            "AiFactoryExistingVpc",
            vpc_id=vpc_id
        )
        reply_ai_resource_registry.add_resource("AI_FACTORY_EXISTING_VPC", ai_factory_existing_vpc)
        lambda_stack = LambdaImagesStack(
            self, "lamdastackservices", resource_prefix=extra_configuration["resource_prefix"]
        )

        # # setup OSS
        oss_stack = OpenSearchServerlessInfraStack(self, "OpenSearchServerlessInfraStack",
                                                   resource_prefix=resource_prefix, envname=envname,
                                                   reply_ai_resource_registry=reply_ai_resource_registry,
                                                   collection_name=extra_configuration.get("KB_CONFIGURATION").get(
                                                       "OSS_COLLECTION_NAME"),
                                                   index_name=extra_configuration.get("KB_CONFIGURATION").get(
                                                       "OSS_INDEX_NAME")
                                                   )

        # create Knowledgebase and datasource
        kb_infra_stack = KbInfraStack(
            self,
            "KbInfraStack",
            resource_prefix=resource_prefix,
            envname=envname,
            extra_configuration=extra_configuration,
            reply_ai_resource_registry=reply_ai_resource_registry,
            oss_stack=oss_stack,
            embedding_model_id=extra_configuration["EMBEDDING_MODEL_ID"][0],
            chunking_strategy=extra_configuration["CHUNKING_STRATEGY"][1],
            max_tokens=extra_configuration["MAX_TOKENS"],
            overlap_percentage=extra_configuration["OVERLAP_PERCENTAGE"],
            lambda_service=lambda_stack.lambdas_services,
        )

        # # create GenAI Layer
        gen_ai_layer_stack = GenAiLayer(self, "GenAiLayer",
                                        ai_factory_vpc=ai_factory_existing_vpc,
                                        resource_prefix=extra_configuration["resource_prefix"],
                                        envname=envname,
                                        reply_ai_resource_registry=reply_ai_resource_registry,
                                        extra_configuration=extra_configuration,
                                        kb_infra_stack=kb_infra_stack,
                                        attr_knowledge_base_id=kb_infra_stack.attr_knowledge_base_id,
                                        lambda_service=lambda_stack.lambdas_services,
                                        prod_sizing=False,
                                        bedrock_engine_region=extra_configuration.get("BEDROCK_REGION_NAME"),
                                        )
