import logging
import os

import boto3
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)


class S3Manager:
    def __init__(self):
        pass

    @staticmethod
    def client(region=None):
        """
        Returns a boto3 S3 client with the specified region or default region.
        """
        if os.getenv("AWS_DEFAULT_PROFILE"):
            return boto3.Session(profile_name=os.getenv("AWS_DEFAULT_PROFILE")).client(service_name='s3',
                                                                                        region_name=region)
        else:
            return boto3.Session().client(service_name='s3',
                                          region_name=region)

    @staticmethod
    def bucket_exists(bucket_name, region=os.getenv("CDK_DEFAULT_REGION")):
        """
        Check if an S3 bucket exists.

        :param bucket_name: Name of the bucket.
        :param region: AWS region.
        :return: True if the bucket exists, False otherwise.
        """
        try:
            S3Manager.client(region).head_bucket(Bucket=bucket_name)
            log.info(f"Bucket '{bucket_name}' exists.")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                log.warning(f"Bucket '{bucket_name}' does not exist. The stack will create it.")
            else:
                log.error(f"Error checking bucket: {e}: on {bucket_name}")
            return False


