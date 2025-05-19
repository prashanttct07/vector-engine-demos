from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import json
import boto3
import os
import sys, getopt

#provide file name
json_file_path = "sample-movies.json"

# Set the vector size for Titan Embeddings model
vector_size = 1536  # Amazon Titan Embeddings model dimension

# Initialize Bedrock client with explicit region
region = os.environ.get('AOSS_VECOTRSEARCH_REGION')
bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)

def generate_embedding(text):
    """Generate embeddings using Amazon Bedrock Titan Embeddings model"""
    response = bedrock_runtime.invoke_model(
        modelId='amazon.titan-embed-text-v1',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            'inputText': text
        })
    )
    
    response_body = json.loads(response['body'].read())
    return response_body['embedding']

def semantic_search(json_file_path, index_name, client):
    # Search for the Documents
    q = input("What are you looking for? ")
    
    # Generate embedding for the query using Bedrock
    q_vector = generate_embedding(q)
    
    query = {
      "size": 20,
      "fields": ["title", "plot"],
      "_source": False,
      "query": {
        "knn": {
          "v_title": {
            "vector": q_vector,
            "k": 20  # Number of results to return
          }
        }
      }
    }
    
    print(query)
    
    response = client.search(
        body=query,
        index=index_name
    )
    
    print('\nSearch results:')
    print(response)
    
def main(argv):
    host = os.environ.get('AOSS_VECOTRSEARCH_ENDPOINT')
    region = os.environ.get('AOSS_VECOTRSEARCH_REGION')
    index = "opensearch_movies"
    service = 'aoss'

    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service,
    session_token=credentials.token)
    
    # Create an OpenSearch client
    client = OpenSearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        timeout = 300,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )
    semantic_search(json_file_path, index, client)
    
if __name__ == '__main__':
    main(sys.argv[1:])
