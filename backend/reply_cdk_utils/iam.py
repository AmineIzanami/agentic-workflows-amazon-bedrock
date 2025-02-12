import json
import os

from aws_cdk import aws_iam as iam, Stack


class IamManager:

    def __init__(self):
        pass

    @staticmethod
    def create_function_role(
        stack: Stack, envname: str, resource_prefix: str, fn_name: str
    ):
        role_name = f"{resource_prefix}-{envname}-{fn_name}-role"

        role_inline_policy = iam.Policy(
            stack,
            f"{resource_prefix}-{envname}-{fn_name}-policy",
            policy_name=f"{resource_prefix}-{envname}-{fn_name}-policy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "secretsmanager:GetSecretValue",
                        "kms:Decrypt",
                        "secretsmanager:DescribeSecret",
                        "kms:Encrypt",
                        "sqs:ReceiveMessage",
                        "kms:GenerateDataKey",
                        "sqs:*",
                        "ssm:GetParametersByPath",
                        "ssm:GetParameters",
                        "ssm:GetParameter",
                        "dynamodb:*",
                        "lambda:*",
                    ],
                    resources=[
                        f"arn:aws:secretsmanager:{stack.region}:{stack.account}:secret:*{resource_prefix}*",
                        f"arn:aws:kms:{stack.region}:{stack.account}:key/*",
                        f"arn:aws:sqs:{stack.region}:{stack.account}:*{resource_prefix}*",
                        f"arn:aws:ssm:*:{stack.account}:parameter/*{resource_prefix}*",
                        f"arn:aws:dynamodb:{stack.region}:{stack.account}:table/*{resource_prefix}*",
                        f"arn:aws:dynamodb:{stack.region}:{stack.account}:table/*{resource_prefix}*/*",
                        f"arn:aws:lambda:{stack.region}:{stack.account}:function:*{resource_prefix}*",
                        f"arn:aws:lambda:{stack.region}:{stack.account}:function:*{resource_prefix}*/*",
                    ],
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
                        f"arn:aws:s3:::{resource_prefix}-{envname}-{stack.account}-{stack.region}-*/*",
                        f"arn:aws:s3:::{resource_prefix}-{envname}-{stack.account}-{stack.region}-*",
                        f"arn:aws:logs:{stack.region}:{stack.account}:log-group:*{resource_prefix}*:log-stream:*",
                        f"arn:aws:logs:{stack.region}:{stack.account}:log-group:*{resource_prefix}*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "logs:DescribeQueries",
                        "logs:StopQuery",
                        "logs:GetQueryResults",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "ec2:CreateNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface",
                        "ec2:AssignPrivateIpAddresses",
                        "ec2:UnassignPrivateIpAddresses",
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords",
                        "xray:GetSamplingRules",
                        "xray:GetSamplingTargets",
                        "xray:GetSamplingStatisticSummaries",
                    ],
                    resources=["*"],
                ),
            ],
        )
        role = iam.Role(
            stack,
            role_name,
            role_name=role_name,
            inline_policies={
                f"{resource_prefix}-{envname}-{fn_name}-inline": role_inline_policy.document
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess"
                ),
            ],
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        return role
