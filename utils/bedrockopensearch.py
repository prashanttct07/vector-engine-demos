from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
import os
import sys
import json
from langchain.llms.bedrock import Bedrock

module_path = "./"
sys.path.append(os.path.abspath(module_path))
from utils import bedrock

# Set the desired vector size for Titan Embeddings
vector_size = 1536

# OpenSearch
host = os.environ.get('AOSS_VECOTRSEARCH_ENDPOINT')
region = os.environ.get('AOSS_VECOTRSEARCH_REGION')

# Bedrock Clients connection
boto3_bedrock = bedrock.get_bedrock_client(
    assumed_role=os.environ.get("AOSS_BEDROCK_ASSUME_ROLE", None),
    region=os.environ.get("AOSS_VECOTRSEARCH_REGION", None),
    runtime=True
)

# Function to generate embeddings using Bedrock
def generate_embedding(text):
    """Generate embeddings using Amazon Bedrock Titan Embeddings model"""
    response = boto3_bedrock.invoke_model(
        modelId='amazon.titan-embed-text-v1',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            'inputText': text
        })
    )
    
    response_body = json.loads(response['body'].read())
    return response_body['embedding']

# - create the LLM Model
claude_llm = Bedrock(model_id="anthropic.claude-instant-v1", client=boto3_bedrock, model_kwargs={'max_tokens_to_sample':1000})
titan_llm = Bedrock(model_id= "amazon.titan-tg1-large", client=boto3_bedrock)

# - Create Prompts
def get_claude_prompt(context, user_question, knowledgebase_filter):
    if knowledgebase_filter:
        prompt = f"""Human: Answer the question based on the information provided. If the answer is not in the context, say "I don't know, answer not found in the documents."
        <context>
        {context}
        </context>
        <question>
        {user_question}
        </question>
        Assistant:"""
        return prompt
    else:
        prompt = f"""Human: Answer the question as below:"
        <question>
        {user_question}
        </question>
        Assistant:"""
        return prompt

def get_titan_prompt(context, user_question, knowledgebase_filter):
    if knowledgebase_filter:
        prompt = f"""Answer the below question based on the context provided. If the answer is not in the context, say "I don't know, answer not found in the documents".
        {context}
        {user_question}
        """
        return prompt
    else:
        prompt = f"""Answer the question as below:".
        {user_question}
        """
        return prompt

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

# Define queries for OpenSearch
def query_qna(query, index):
    query_embedding = generate_embedding(query)
    query_qna = {
        "size": 3,
        "fields": ["content", "title"],
        "_source": False,
        "query": {
            "knn": {
            "v_content": {
                "vector": query_embedding,
                "k": 3  # Number of nearest neighbors to find
            }
            }
        }
    }

    relevant_documents = client.search(
        body = query_qna,
        index = index
    )
    return relevant_documents

def query_movies(query, sort, genres, rating, index):
    if sort == 'year':
        sort_type = "year"
    elif sort == 'rating':
        sort_type = "rating"
    else:
        sort_type = "_score"

    if genres == '':
        genres = '*'

    if rating == '':
        rating = 0

    # Generate embedding using Bedrock instead of SentenceTransformer
    query_embedding = generate_embedding(query)
    
    query_knn = {
        "size": 3,
        "sort": [
            {
                sort_type: {
                    "order": "desc"
                }
            }
        ],
        "_source": {
            "includes": [
                "title",
                "plot",
                "rating",
                "year",
                "poster",
                "genres"
            ]
        },
        "query": {
            "bool": {
                "should": [
                    {
                        "knn": {
                            "v_plot": {
                                "vector": query_embedding,
                                "k": 3  # Number of nearest neighbors to find
                            }
                        }
                    },
                    {
                        "knn": {
                            "v_title": {
                                "vector": query_embedding,
                                "k": 3  # Number of nearest neighbors to find
                            }
                        }
                    }
                ],
                "filter": [
                    {
                        "query_string": {
                            "query": genres,
                            "fields": [
                                "genres"
                            ]
                        }
                    },
                    {
                      "range": {
                        "rating": {
                          "gte": rating
                        }
                      }
                    }
                ]
            }
        }
    }
    response_knn = client.search(
        body = query_knn,
        index = index
    )

    # Extract relevant information from the search result
    hits_knn = response_knn['hits']['hits']
    doc_count_knn = response_knn['hits']['total']['value']
    results_knn = [{'genres':  hit['_source']['genres'],'poster':  hit['_source']['poster'],'title': hit['_source']['title'], 'rating': hit['_source']['rating'], 'year': hit['_source']['year'], 'plot' : hit['_source']['plot']} for hit in hits_knn]

    query_kw = {
        "size": 3,
        "sort": [
            {
                sort_type: {
                    "order": "desc"
                }
            }
        ],
        "_source": {
            "includes": [
                "title",
                "plot",
                "rating",
                "year",
                "poster",
                "genres"
            ]
        },
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": query,
                        "fields": ["plot", "title"]
                    }
                },
                "filter": [
                    {
                        "query_string": {
                            "query": genres,
                            "fields": [
                                "genres"
                            ]
                        }
                    },
                    {
                      "range": {
                        "rating": {
                          "gte": rating
                        }
                      }
                    }
                ]
            }
        }
    }

    response_kw = client.search(
        body = query_kw,
        index = index
    )

    # Extract relevant information from the search result
    hits_kw = response_kw['hits']['hits']
    doc_count_kw = response_kw['hits']['total']['value']
    results_kw = [{'genres':  hit['_source']['genres'],'poster':  hit['_source']['poster'],'title': hit['_source']['title'], 'rating': hit['_source']['rating'], 'year': hit['_source']['year'], 'plot' : hit['_source']['plot']} for hit in hits_kw]

    return results_knn, doc_count_knn, results_kw, doc_count_kw
