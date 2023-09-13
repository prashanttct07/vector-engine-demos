#!/bin/sh

python3 -m ensurepip --upgrade
python3 -m pip install opensearch-py boto3 requests_aws4auth sentence_transformers pydantic langchain pypdf


echo "Creating directory"
mkdir -p ./dependencies && \
cd ./dependencies && \
echo "Downloading dependencies"
curl -sS https://d2eo22ngex1n9g.cloudfront.net/Documentation/SDK/bedrock-python-sdk.zip > sdk.zip
echo "Unpacking dependencies"
unzip sdk.zip && \
rm sdk.zip

python3 -m pip install dependencies/botocore-1.31.21-py3-none-any.whl dependencies/boto3-1.28.21-py3-none-any.whl dependencies/awscli-1.29.21-py3-none-any.whl --force-reinstall
