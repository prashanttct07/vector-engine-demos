import json
import boto3
import os
from typing import Any, Dict, List, Optional
from pydantic import root_validator
from time import sleep
from enum import Enum
import boto3
from botocore.config import Config

# Create a boto3 client for Amazon Bedrock, with optional configuration overrides    
#     Parameters
#     ----------
#     assumed_role :
#         Optional ARN of an AWS IAM role to assume for calling the Bedrock service. If not
#         specified, the current active credentials will be used.
#
#     region :
#         Optional name of the AWS Region in which the service should be called (e.g. "us-east-1").
#         If not specified, AWS_REGION or AWS_DEFAULT_REGION environment variable will be used.
#
#     url_override :
#         Optional override for the Bedrock service API Endpoint. If setting this, it should usually
#         include the protocol i.e. "https://..."

def get_bedrock_client(assumed_role=None, region='us-east-1', url_override = None):
    boto3_kwargs = {}
    session = boto3.Session()

    target_region = os.environ.get('AWS_DEFAULT_REGION',region)

    print(f"Create new client\n  Using region: {target_region}")
    if 'AWS_PROFILE' in os.environ:
        print(f"  Using profile: {os.environ['AWS_PROFILE']}")

    retry_config = Config(
        region_name = target_region,
        retries = {
            'max_attempts': 10,
            'mode': 'standard'
        }
    )

    boto3_kwargs = {}

    if assumed_role:
        print(f"  Using role: {assumed_role}", end='')
        sts = session.client("sts")
        response = sts.assume_role(
            RoleArn=str(assumed_role), #
            RoleSessionName="langchain-llm-1"
        )
        # print(" ... successful!")
        boto3_kwargs['aws_access_key_id']=response['Credentials']['AccessKeyId']
        boto3_kwargs['aws_secret_access_key']=response['Credentials']['SecretAccessKey']
        boto3_kwargs['aws_session_token']=response['Credentials']['SessionToken']

    if url_override:
        boto3_kwargs['endpoint_url']=url_override

    bedrock_client = session.client(
        service_name='bedrock',
        config=retry_config,
        region_name= target_region,
        **boto3_kwargs
        )
 
    # print("boto3 Bedrock client successfully created!")
    # print(bedrock_client._endpoint)
    return bedrock_client


