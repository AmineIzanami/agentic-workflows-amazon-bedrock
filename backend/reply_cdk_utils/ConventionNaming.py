import json
import os

from aws_cdk import (
    aws_iam as iam,
    aws_sqs as sqs,
    aws_kms as kms,
    RemovalPolicy,
    Stack,
    Duration
)
from enum import Enum
import re

class Scope(Enum):
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"


class ConventionNamingManager:

    def __init__(self):
        pass

    @staticmethod
    def get_s3_bucket_name_convention(*,
                                      stack: Stack,
                                      resource_prefix: str,
                                      envname: str,
                                      bucket_name: str) -> str:
        pattern = r'^[a-z0-9]([a-z0-9\-]{1,61}[a-z0-9])?$'
        match = re.match(pattern, bucket_name)
        if match:
            return f"{resource_prefix.lower()}-{envname}-{stack.account}-{stack.region}-{bucket_name}"
        else:
            raise Exception(f"Invalid bucket name: {bucket_name}")

    @staticmethod
    def get_lambda_name_convention(resource_prefix: str,
                                   envname: str,
                                   lambda_name: str) -> str:
        pattern = r'^[a-zA-Z0-9-_]{1,64}$'
        match = re.match(pattern, lambda_name)
        if match:
            return f"{resource_prefix}-{envname}-{lambda_name}"
        else:
            raise Exception(f"Invalid lambda name: {lambda_name}")

    @staticmethod
    def get_vpc_name_convention(resource_prefix: str,
                                envname: str,
                                vpc_name: str) -> str:
        pattern = r'^[a-zA-Z0-9-_]{1,64}$'
        match = re.match(pattern, vpc_name)
        if match:
            return f"{resource_prefix}-{envname}-{vpc_name}"
        else:
            raise Exception(f"Invalid VPC name: {vpc_name}")

    @staticmethod
    def get_rds_name_convention(resource_prefix: str,
                                envname: str,
                                rds_name: str) -> str:
        pattern = r'^[a-zA-Z0-9-]{1,63}$'
        match = re.match(pattern, rds_name)
        if match:
            return f'{resource_prefix}-{envname}-{rds_name}'
        else:
            raise Exception(f"Invalid RDS name: {rds_name}")

    @staticmethod
    def get_kendra_name_convention(resource_prefix: str,
                                   envname: str,
                                   index_name: str) -> str:
        pattern = r'^[a-zA-Z0-9-]{1,63}$'
        match = re.match(pattern, index_name)
        if match:
            return f'{resource_prefix}-{envname}-{index_name}'
        else:
            raise Exception(f"Invalid KENDRA name: {index_name}")

    @staticmethod
    def get_ddb_name_convention(resource_prefix: str,
                                envname: str,
                                table_name: str) -> str:
        pattern = r'^[a-zA-Z0-9_.-]{3,255}$'
        match = re.match(pattern, table_name)
        if match:
            return f'{resource_prefix}-{envname}-{table_name}'
        else:
            raise Exception(f"Invalid DDB name: {table_name}")

    @staticmethod
    def get_graphql_name_convention(resource_prefix: str,
                                    envname: str,
                                    api_name: str) -> str:
        pattern = r'^[a-zA-Z0-9-_]{1,64}$'
        match = re.match(pattern, api_name)
        if match:
            return f'{resource_prefix}-{envname}-{api_name}'
        else:
            raise Exception(f"Invalid GraphQL API name: {api_name}")

    @staticmethod
    def get_alb_name_convention(resource_prefix: str,
                                envname: str,
                                alb_name: str) -> str:
        pattern = r'^[a-zA-Z0-9-]{1,32}$'
        match = re.match(pattern, alb_name)
        if match:
            return f'{resource_prefix}-{envname}-{alb_name}'
        else:
            raise Exception(f"Invalid ALB name: {alb_name}")

    @staticmethod
    def get_sqs_name_convention(resource_prefix: str,
                                envname: str,
                                queue_name: str) -> str:
        pattern = r'^[a-zA-Z0-9-_]{1,80}$'
        match = re.match(pattern, queue_name)
        if match:
            return f'{resource_prefix}-{envname}-{queue_name}'
        else:
            raise Exception(f"Invalid SQS name: {queue_name}")

    @staticmethod
    def get_ssm_name_convention(resource_prefix: str,
                                envname: str,
                                parameter_name: str) -> str:
        pattern = r'^[a-zA-Z0-9/_\.-]{1,2048}$'
        match = re.match(pattern, parameter_name)
        if match:
            return f'/{resource_prefix}/{envname}/infrastructure/{parameter_name}'
        else:
            raise Exception(f"Invalid parameter name: {parameter_name}")

    @staticmethod
    def get_secret_name_convention(resource_prefix: str,
                                   envname: str,
                                   secret_name: str) -> str:
        pattern = r'^[a-zA-Z0-9/_\.-]{1,2048}$'
        match = re.match(pattern, secret_name)
        if match:
            return f'/{resource_prefix}/{envname}/infrastructure/{secret_name}'
        else:
            raise Exception(f"Invalid Secret name: {secret_name}")

    @staticmethod
    def get_iam_role_name_convention(resource_prefix: str,
                                     envname: str,
                                     role_name: str) -> str:
        pattern = r'^[a-zA-Z0-9-_]{1,64}$'
        match = re.match(pattern, role_name)
        if match:
            return f"{resource_prefix}-{envname}-{role_name}"
        else:
            raise Exception(f"Invalid IAM role name: {role_name}")

    @staticmethod
    def get_knowledge_base_name_convention(resource_prefix: str,
                                           envname: str,
                                           knowledge_base_name: str) -> str:
        pattern = r'^[a-zA-Z0-9-_]{1,64}$'
        match = re.match(pattern, knowledge_base_name)
        if match:
            return f"{resource_prefix}-{envname}-{knowledge_base_name}"
        else:
            raise Exception(f"Invalid Knowledge Base name: {knowledge_base_name}")

    @staticmethod
    def get_opensearch_collection_name_convention(resource_prefix: str,
                                                  envname: str,
                                                  collection_name: str) -> str:
        pattern = r'^[a-z][a-z0-9-]{2,31}$'
        match = re.match(pattern, collection_name)
        if match:
            return f"{resource_prefix}-{envname}-{collection_name}"
        else:
            raise Exception(f"Invalid OpenSearch collection name: {collection_name}")
