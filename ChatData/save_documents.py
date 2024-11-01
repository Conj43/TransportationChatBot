import os
import json
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import WebBaseLoader
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access USER_AGENT and OpenAI API key
user_agent = os.getenv('LANGCHAIN_USER_AGENT')
openai_api_key = os.getenv('OPENAI_API_KEY')

# Define the URL and file path for saving documents
urls = ["https://www.britannica.com/place/Missouri-state"]
documents_file = "documents.json"

# Load documents from web and save to file
web_loader = WebBaseLoader(urls, header_template={'LANGCHAIN_USER_AGENT': user_agent})
documents = web_loader.load()

# Convert Document objects to dictionaries for JSON serialization
documents_dict = [{'content': doc.page_content, 'metadata': doc.metadata} for doc in documents]

# Save documents to a JSON file
with open(documents_file, 'w') as f:
    json.dump(documents_dict, f)

print(f"Documents saved to {documents_file}.")
