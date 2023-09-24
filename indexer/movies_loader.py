from sentence_transformers import SentenceTransformer
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import json
import boto3
import os
import time
import sys, getopt

# Load the SentenceTransformer model
model_name = 'sentence-transformers/msmarco-distilbert-base-tas-b'
model = SentenceTransformer(model_name)

# Set the desired vector size
vector_size = 768

def full_load(json_file_path, index_name, client):
    
# if index_name exists in collection, don't run this again 
    # create a new index
    if not client.indices.exists(index=index_name):
        index_body = {
            "settings": {
                "index.knn": True
          },
          'mappings': {
            'properties': {
              "title": {"type":"text","fields":{"keyword":{"type":"keyword","ignore_above":256}}},
              "v_title": { "type": "knn_vector", "dimension": vector_size },
              "plot": {"type":"text","fields":{"keyword":{"type":"keyword","ignore_above":256}}},
              "v_plot": { "type": "knn_vector", "dimension": vector_size },
              "actors": {"type":"text","fields":{"keyword":{"type":"keyword","ignore_above":256}}},
              "certificate": {"type":"text","fields":{"keyword":{"type":"keyword","ignore_above":256}}},
              "directors": {"type":"text","fields":{"keyword":{"type":"keyword","ignore_above":256}}},
              "genres": {"type":"text","fields":{"keyword":{"type":"keyword","ignore_above":256}}},
              "image_url": {"type":"text","fields":{"keyword":{"type":"keyword","ignore_above":256}}},
              "gross_earning": {"type":"float"},
              "metascore": {"type":"float"},
              "rating": {"type":"double"},
              "time_minute": {"type":"long"},
              "vote": {"type":"long"},
              "year": {"type":"long"}
            }
          }
        }

        client.indices.create(
          index=index_name, 
          body=index_body
        )
        time.sleep(5)
    
    actions = []
    i = 0
    j = 0
    action = {"index": {"_index": index_name}}

    # Read and index the JSON data
    with open(json_file_path, 'r') as file:
        for item in file:
            json_data = json.loads(item)
            if 'index' in json_data:
                continue

            #encode title
            title = json_data['title']
            v_title = model.encode([title])[0].tolist()
            json_data['v_title'] = v_title
    
            if 'plot' in json_data:
            #encode plot
                plot = json_data['plot']
                v_plot = model.encode([plot])[0].tolist()
                json_data['v_plot'] = v_plot
    
            # Prepare bulk request
            actions.append(action)
            actions.append(json_data.copy())
    
            if(i > 10 ):
                client.bulk(body=actions)
                print(f"bulk request sent with size: {i}")
                print(f"total docs sent so far: {j}")
                i = 0
                actions = []
            i += 1
            j += 1


def main(argv):
    host = os.environ.get('AOSS_VECOTRSEARCH_ENDPOINT')
    region = os.environ.get('AOSS_VECOTRSEARCH_REGION')
    index = "opensearch_movies"
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
    full_load(index, client)

if __name__ == '__main__':
    main(sys.argv[1:])
