#!/bin/sh

set -e

echo "(Re)-creating directory"
rm -rf dependencies
mkdir dependencies
cd dependencies
echo "Downloading dependencies"
curl -sS https://d2eo22ngex1n9g.cloudfront.net/Documentation/SDK/bedrock-python-sdk.zip > sdk.zip
echo "Unpacking dependencies"

# (If you don't have `unzip` utility installed)
if command -v unzip &> /dev/null
then
    unzip sdk.zip && rm sdk.zip && echo "Done"
else
    echo "'unzip' command not found: Trying to unzip via Python"
    python -m zipfile -e sdk.zip . && rm sdk.zip && echo "Done"
fi
cd ..

# create the virtual environment
python3 -m venv .env
# Install into the virtual environment
source .env/bin/activate

# download requirements
.env/bin/python -m ensurepip --upgrade
.env/bin/python -m pip install opensearch-py requests_aws4auth
.env/bin/python -m pip install boto3 langchain pypdf pydantic
.env/bin/python -m pip install sentence_transformers

.env/bin/python -m pip install  --no-build-isolation --force-reinstall \
    dependencies/awscli-*-py3-none-any.whl \
    dependencies/boto3-*-py3-none-any.whl \
    dependencies/botocore-*-py3-none-any.whl

.env/bin/python -m pip install streamlit
