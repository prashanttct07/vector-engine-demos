
########
import requests
import sys, getopt
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
import json
import os
import time
from langchain.text_splitter import CharacterTextSplitter
from sentence_transformers import SentenceTransformer

# Load the SentenceTransformer model
model_name = 'sentence-transformers/msmarco-distilbert-base-tas-b'
model = SentenceTransformer(model_name)

# Set the desired vector size (it should be alligned with the model you are using)
vector_size = 768

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

def index_embedding(content, title, repository, client, index):
    actions =[]
    bulk_size = 0
    action = {"index": {"_index": index}}
    
    text_splitter = CharacterTextSplitter(
    # Set a really small chunk size, just to show.
    chunk_size = 1000,
    chunk_overlap  = 100,
    separator=" "
    )

    docs = text_splitter.split_text(content)
    print (f"Total Chunk {len(docs)} for {title}")
    for doc in docs: 
        # sample_embedding = np.array(bedrock_embeddings.embed_query(document.page_content))
        embeddings = model.encode(doc)
        vector_document = {
            "title": title,
            "content": content,
            "v_content": embeddings,
            "repository": repository
        }
        # print (vector_document)
        actions.append(action)
        actions.append(vector_document)

        bulk_size+=1
        if(bulk_size > 100 ):
            client.bulk(body=actions)
            print(f"bulk request sent with size: {bulk_size}")
            bulk_size = 0

    #ingest remaining documents
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
    print (repo_url)
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
            crawl_github_subfolder_recursive(owner, repo, subfolder_path)


def main(argv):
    host = os.environ.get('OPENSEARCH_HOST')
    region = os.environ.get('OPENSEARCH_REGION')
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
