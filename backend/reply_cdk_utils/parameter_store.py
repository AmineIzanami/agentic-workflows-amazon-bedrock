import logging
import os

import boto3
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)


def ns2d(**kwargs):
    return kwargs


class ParameterStoreManager:
    def __init__(self):
        pass

    @staticmethod
    def client(region=None):
        if os.getenv("AWS_DEFAULT_PROFILE"):
            return boto3.Session(profile_name=os.getenv("AWS_DEFAULT_PROFILE")).client(service_name='ssm',
                                                                                       region_name=region)
        else:
            return boto3.Session().client(service_name='ssm',
                                          region_name=region)

    @staticmethod
    def get_parameter_value(AwsAccountId=None, region=os.getenv("CDK_DEFAULT_REGION"), parameter_path=None):
        if not parameter_path:
            raise Exception('Parameter name is None')
        try:
            parameter_value = \
                ParameterStoreManager.client(region=region).get_parameter(Name=parameter_path)['Parameter'][
                    'Value']
        except ClientError as e:
            return None
        return parameter_value

    @staticmethod
    def update_parameter(AwsAccountId, region, parameter_name, parameter_value):
        if not parameter_name:
            raise Exception('Parameter name is None')
        if not parameter_value:
            raise Exception('Parameter value is None')
        try:
            response = ParameterStoreManager.client(region).put_parameter(Name=parameter_name, Value=parameter_value,
                                                                          Overwrite=True)['Version']
        except ClientError as e:
            raise Exception(e)
        else:
            return str(response)
