import requests
import sys, getopt
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
import json
import os
import time

# Initialize Bedrock client
bedrock_client = boto3.client('bedrock-runtime', region_name=os.environ.get('AOSS_VECOTRSEARCH_REGION'))

# Set the desired vector size for Titan Embeddings model
vector_size = 1536  # Titan Embeddings G1 - Text produces 1536-dimensional vectors

# Usage example For service docs
owner = "awsdocs"
repo = "amazon-opensearch-service-developer-guide"
subfolder = "doc_source"

# Usage example For Opensearch project docs
# owner = "opensearch-project"
# repo = "documentation-website"
# subfolder = ""

# Usage example For Opensearch project blogs
# owner = "opensearch-project"
# repo = "project-website"
# subfolder = "_posts"

def get_bedrock_embedding(text):
    """Generate embeddings using Amazon Bedrock's Titan Embeddings model"""
    try:
        response = bedrock_client.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'inputText': text
            })
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['embedding']
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return None

def split_text_with_bedrock(content, chunk_size=1000, chunk_overlap=100):
    """Split text into chunks using simple text processing"""
    chunks = []
    content_length = len(content)
    
    # Process content in chunks
    for i in range(0, content_length, chunk_size - chunk_overlap):
        # Get chunk with appropriate size
        end_idx = min(i + chunk_size, content_length)
        chunk = content[i:end_idx]
        
        # Only add non-empty chunks that meet minimum size requirements
        if len(chunk.strip()) > 50:  # Minimum size threshold
            chunks.append(chunk)
            
    return chunks

def index_embedding(content, title, repository, client, index):
    actions = []
    bulk_size = 0
    action = {"index": {"_index": index}}
    
    # Split text using our custom function instead of LangChain
    docs = split_text_with_bedrock(content, chunk_size=1000, chunk_overlap=100)
    
    print(f"Total Chunk {len(docs)} for {title}")
    for doc in docs: 
        # Generate embeddings using Bedrock instead of SentenceTransformer
        embeddings = get_bedrock_embedding(doc)
        
        if embeddings:
            vector_document = {
                "title": title,
                "content": doc,  # Store the chunk, not the entire content
                "v_content": embeddings,
                "repository": repository
            }
            
            actions.append(action)
            actions.append(vector_document)

            bulk_size += 1
            if bulk_size > 100:
                client.bulk(body=actions)
                print(f"bulk request sent with size: {bulk_size}")
                actions = []  # Reset actions after bulk
                bulk_size = 0

    # Ingest remaining documents
    if actions:
        print("Sending remaining documents with size: ", bulk_size)
        client.bulk(body=actions)

def crawl_github_subfolder_recursive(owner, repo, subfolder, client, index):
    # Create an index if it does not exist
    if not client.indices.exists(index=index):
        index_body = {
            "settings": {
                "index.knn": True
            },
            'mappings': {
                'properties': {
                    "repository": { "type": "text"},
                    "title": { "type": "text"},
                    "content": { "type": "text"},
                    "v_content": { "type": "knn_vector", "dimension": vector_size }
                }
            }
        }
    
        client.indices.create(
            index=index, 
            body=index_body
        )
        time.sleep(5)

    # Fetch repository information
    repo_url = f"https://api.github.com/repos/{owner}/{repo}"
    repo_info = requests.get(repo_url).json()
    print(repo_url)
    
    # Fetch contents of the subfolder
    contents_url = repo_info["contents_url"].replace("{+path}", subfolder)
    contents = requests.get(contents_url).json()
    
    # Filter and process files recursively
    for item in contents:
        print(f"title: {item['name']}")
        if item["type"] == "file":
            if item["name"].endswith(".md"):
                # Download the file
                download_url = item["download_url"]
                response = requests.get(download_url)
                content = response.text

                # Index the content to OpenSearch
                index_embedding(content, item["name"], f"{owner}/{repo}", client, index)

        elif item["type"] == "dir":
            # Recursively crawl subdirectories
            subfolder_path = os.path.join(subfolder, item["name"])
            crawl_github_subfolder_recursive(owner, repo, subfolder_path, client, index)

def main(argv):
    host = os.environ.get('AOSS_VECOTRSEARCH_ENDPOINT')
    region = os.environ.get('AOSS_VECOTRSEARCH_REGION')
    index = "opensearch_qna"
    service = 'aoss'

    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service,
                   session_token=credentials.token)

    # Build the OpenSearch client
    client = OpenSearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        timeout = 300,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )
    print(f"OpenSearch Client - Sending to Amazon OpenSearch Serverless host {host} in Region {region} \n")
    crawl_github_subfolder_recursive(owner, repo, subfolder, client, index)

if __name__ == '__main__':
    main(sys.argv[1:])
