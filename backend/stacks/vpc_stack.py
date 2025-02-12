from constructs import Construct
from aws_cdk import Stack

from typing import List

from aws_cdk import (
    aws_ec2 as ec2,
    Fn,
    aws_ssm as ssm,
    aws_s3 as s3,
    RemovalPolicy,
    Duration,
    CfnOutput,
)

from reply_cdk_utils.ConventionNaming import ConventionNamingManager
from reply_cdk_utils.parameter_store import ParameterStoreManager


class VpcStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        resource_prefix: str,
        envname: str = None,
        exists: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.vpc_cidr = "192.168.0.0/16"
        self.resource_prefix = resource_prefix
        self.envname = envname
        self.vpc_name = ConventionNamingManager.get_vpc_name_convention(
            resource_prefix=resource_prefix, envname=envname, vpc_name="vpcname"
        )
        if not exists:
            self.__create_vpc()

    def get_existing_vpc_stack(self):
        all_availability_zones = Fn.get_azs(region=self.region)

        availability_zones = [
            Fn.select(0, all_availability_zones),
            Fn.select(1, all_availability_zones),
            Fn.select(2, all_availability_zones),
        ]

        self.private_subnet_ids: List[str] = [
            ParameterStoreManager.get_parameter_value(
                parameter_path="/landingzone/vpc/private-subnet-1-id"
            ),
            ParameterStoreManager.get_parameter_value(
                parameter_path="/landingzone/vpc/private-subnet-2-id"
            ),
            ParameterStoreManager.get_parameter_value(
                parameter_path="/landingzone/vpc/private-subnet-3-id"
            ),
        ]

        self.private_subnet_route_table_ids: List[str] = [
            ParameterStoreManager.get_parameter_value(
                parameter_path="/landingzone/vpc/route-table-private-subnet-1-id"
            ),
            ParameterStoreManager.get_parameter_value(
                parameter_path="/landingzone/vpc/route-table-private-subnet-2-id"
            ),
            ParameterStoreManager.get_parameter_value(
                parameter_path="/landingzone/vpc/route-table-private-subnet-3-id"
            ),
        ]

        self.vpc: ec2.Vpc = ec2.Vpc.from_vpc_attributes(
            self,
            f"{self.resource_prefix}-vpc",
            vpc_id=ParameterStoreManager.get_parameter_value(
                parameter_path="/landingzone/vpc/vpc-cidr"
            ),
            availability_zones=availability_zones,
            private_subnet_ids=self.private_subnet_ids,
            private_subnet_route_table_ids=self.private_subnet_route_table_ids,
            vpc_cidr_block=ParameterStoreManager.get_parameter_value(
                parameter_path="/landingzone/vpc/vpc-cidr"
            ),
        )

    def __create_vpc(self):
        vpc_name = ConventionNamingManager.get_vpc_name_convention(
            resource_prefix=self.resource_prefix,
            envname=self.envname,
            vpc_name="ai-factory",
        )

        self.audit_bucket = s3.Bucket(
            self,
            id=f"audit-bucket-{self.resource_prefix}",
            # for our testing we will be adding resource prefix to avoid the clash, for the customer we remove the prefix
            bucket_name=ConventionNamingManager.get_s3_bucket_name_convention(
                stack=self,
                resource_prefix=self.resource_prefix,
                envname=self.envname,
                bucket_name="logs-vpc",
            ),
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=False,
            auto_delete_objects=True if self.envname == "dev" else False,
            removal_policy=(
                RemovalPolicy.DESTROY if self.envname == "dev" else RemovalPolicy.RETAIN
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

        self.vpc: ec2.Vpc = ec2.Vpc(
            self,
            "ec2vpc",
            vpc_name=vpc_name,
            ip_addresses=ec2.IpAddresses.cidr(self.vpc_cidr),
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC, name="Public", cidr_mask=20
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    name="Compute",
                    cidr_mask=20,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    name="RDS",
                    cidr_mask=20,
                ),
            ],
            nat_gateways=1,
            flow_logs={
                "flow-logs-s3": {
                    "destination": ec2.FlowLogDestination.to_s3(
                        bucket=self.audit_bucket,
                        key_prefix="vpc-logs/{vpc_name}".format(vpc_name=vpc_name),
                    )
                }
            },
        )

        self.vpc_id = self.vpc.vpc_id

        ssm.StringParameter(
            self,
            "VpcIdParameter",
            parameter_name=f"/vpc/{self.resource_prefix}/{self.envname}/vpc-id",
            string_value=self.vpc.vpc_id,
        )

        if self.vpc.private_subnets:
            self.private_subnets = [
                subnet.subnet_id for subnet in self.vpc.private_subnets
            ]
            ssm.StringParameter(
                self,
                "VpcPrivateSubnets",
                parameter_name=f"/vpc/{self.resource_prefix}/{self.envname}/vpc/private_subnets",
                string_value=(",".join(self.private_subnets)),
            )

        if self.vpc.public_subnets:
            self.public_subnets = [
                subnet.subnet_id for subnet in self.vpc.public_subnets
            ]
            ssm.StringParameter(
                self,
                "VpcPublicSubnets",
                parameter_name=f"/vpc/{self.resource_prefix}/{self.envname}/vpc/public_subnets",
                string_value=(",".join(self.public_subnets)),
            )
