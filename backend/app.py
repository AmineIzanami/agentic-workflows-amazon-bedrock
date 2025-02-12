#!/usr/bin/env python3

import aws_cdk as cdk
from cdk_aspects.reply_aspects import GlobalTaggingAspect
from reply_cdk_utils.runtime_stacks_tagging import TagsUtil
from stacks.core_stack import CoreStack
from stacks.standalone_genai_layer import StandaloneGenAiLayer
from stacks.vpc_stack import VpcStack

app = cdk.App()

environment_name = "dev"
environment_configuration = app.node.try_get_context("DeploymentEnvironments").get(environment_name)

extra_configuration = {
    "resource_prefix": environment_configuration.get('RESOURCE_PREFIX'),
    "vpc_id": environment_configuration.get("VPC_ID"),
    "account_id": environment_configuration.get('ACCOUNT_ID'),
    "KB_DOCS_S3_BUCKET_NAME": environment_configuration.get('KB_DOCS_S3_BUCKET_NAME'),
    "cdk_region": environment_configuration.get('REGION'),
    "tags": environment_configuration.get('STACK-TAGS'),
    "AGENT_FOUNDATION_MODEL": environment_configuration.get("AGENT_FOUNDATION_MODEL"),
    "WORKSPACE_NAME": environment_configuration.get('WORKSPACE_NAME'),
    "KB_CONFIGURATION": environment_configuration.get('KB_CONFIGURATION'),
    "BEDROCK_REGION_NAME": environment_configuration.get('BEDROCK_REGION_NAME'),
    "PROJECT_AGENT_NAME": environment_configuration.get('PROJECT_AGENT_NAME'),
    "AI_FACTORY_REGION_NAME": environment_configuration.get('REGION'),
    "EMBEDDING_MODEL_ID": ["amazon.titan-embed-text-v2:0"],
    "CHUNKING_STRATEGY": {
        0: "Default chunking",
        1: "Fixed-size chunking",
        2: "No chunking",
    },
    "MAX_TOKENS": 512,  # type: ignore
    "OVERLAP_PERCENTAGE": 20,
}

resource_prefix = extra_configuration.get("resource_prefix")
vpc_id = extra_configuration.get("vpc_id")
account_id = extra_configuration.get("account_id")
cdk_region = extra_configuration.get("cdk_region")

env = cdk.Environment(account=account_id, region=cdk_region)

if not extra_configuration.get("vpc_id"):
    existing_vpc_ai_factory = False
    ai_factory_vpc = VpcStack(
        app,
        f"MultiAgentVPC{environment_name}{resource_prefix}",
        resource_prefix=extra_configuration["resource_prefix"],
        envname=environment_name,
        exists=existing_vpc_ai_factory,
    )
    TagsUtil.add_tags(dict_tags=extra_configuration.get("tags"), stack=ai_factory_vpc)

if environment_configuration.get('STANDALONE_GENAI_LAYER'):
    standalone_genai_layer = StandaloneGenAiLayer(app,
                                                  f"MultiAgentNoKb{environment_name}{resource_prefix}",
                                                  resource_prefix= resource_prefix+"nokb",
                                                  envname=environment_name,
                                                  vpc_id=vpc_id,
                                                  env=env,
                                                  prod_sizing=False,
                                                  bedrock_engine_region=extra_configuration.get("BEDROCK_REGION_NAME"),
                                                  extra_configuration=extra_configuration)
    TagsUtil.add_tags(dict_tags=extra_configuration.get("tags"), stack=standalone_genai_layer)
    for _tags_key in extra_configuration.get("tags"):
        cdk.Aspects.of(standalone_genai_layer).add(
            GlobalTaggingAspect(_tags_key, extra_configuration.get("tags").get(_tags_key)))

else:
    core_stack = CoreStack(app, f"ReplyMultiAgent{environment_name}{resource_prefix}",
                           resource_prefix=resource_prefix,
                           envname=environment_name,
                           vpc_id=vpc_id,
                           env=env,
                           extra_configuration=extra_configuration)
    TagsUtil.add_tags(dict_tags=extra_configuration.get("tags"), stack=core_stack)
    for _tags_key in extra_configuration.get("tags"):
        cdk.Aspects.of(core_stack).add(GlobalTaggingAspect(_tags_key, extra_configuration.get("tags").get(_tags_key)))

app.synth()
