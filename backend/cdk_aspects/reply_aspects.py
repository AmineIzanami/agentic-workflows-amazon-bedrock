from typing import Dict, Union

import jsii
from aws_cdk import (aws_s3 as s3, IAspect, Tokenization, Annotations, CfnResource, Tags)
from constructs import Construct


@jsii.implements(IAspect)
class GlobalTaggingAspect:
    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def visit(self, node: Construct) -> None:
        # Only apply tags to CDK resources (CfnResource)
        if isinstance(node, CfnResource):
            Tags.of(node).add(self.key, self.value)


@jsii.implements(IAspect)
class BucketNamingChecker:
    def __init__(self,
                 environment_configuration: Dict[str, Union[Dict, str]],

                 ) -> None:

        self.resource_prefix = environment_configuration.get("RESOURCE_PREFIX")
        self.account_id = environment_configuration.get("ACCOUNT_ID")
        self.cdk_region = environment_configuration.get("REGION")
        self.tags = environment_configuration.get("STACK-TAGS")
        self.envname = self.tags.get("Environment")

    def visit(self, node):
        # See that we're dealing with a CfnBucket
        if isinstance(node, s3.CfnBucket):
            if not node.bucket_name.startswith(
                    f"{self.resource_prefix}-{self.envname}-{node.stack.account}-{node.stack.region}-"):
                Annotations.of(node).add_error(f'Bucket Naming is not compliant : {node.bucket_name}')
