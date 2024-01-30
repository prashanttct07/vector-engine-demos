# Usage example For Crawling github repo (you can change it to use any other github repo as per your choice)
import boto3
import requests
s3 = boto3.resource('s3')
s3_ = boto3.client('s3')
bucket_ = s3_.list_buckets()['Buckets'][0]['Name']

owner = "awsdocs"
repo = "amazon-opensearch-service-developer-guide"
subfolder = "doc_source"
repo_url = f"https://api.github.com/repos/{owner}/{repo}"
repo_info = requests.get(repo_url).json()

# Fetch contents of the subfolder
contents_url = repo_info["contents_url"].replace("{+path}", subfolder)
contents = requests.get(contents_url).json()
for item in contents:
    print(f"title: {item['name']}")
    if item["type"] == "file":
        if item["name"].endswith(".md"):
            # Download the file
            download_url = item["download_url"]
            response = requests.get(download_url)
            content = response.text
            object = s3.Object(
                bucket_name=bucket_, 
                key='kb/'+item['name']
            )
            #Push the contents to s3
            object.put(Body=content)
