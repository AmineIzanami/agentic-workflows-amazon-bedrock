from aws_cdk import (
    # Duration,
    Stack, NestedStack,
)

from constructs import Construct

from aws_cdk.aws_ecr_assets import DockerImageAsset


class LambdaImagesStack(NestedStack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        resource_prefix: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.lambdas_services = DockerImageAsset(
            self,
            f"LmabdasServicesImage{resource_prefix}",
            directory="code/services",
            cache_disabled=True,
        )
