import os
import json
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
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

# Load documents from file if it exists, otherwise load from web
if os.path.exists(documents_file):
    with open(documents_file, 'r') as f:
        documents = json.load(f)
else:
    web_loader = WebBaseLoader(urls, header_template={'LANGCHAIN_USER_AGENT': user_agent})
    documents = web_loader.load()
    
    # Convert Document objects to dictionaries for JSON serialization
    documents_dict = [doc.to_dict() for doc in documents]  # Assuming Document has a to_dict() method

    # Save documents to a JSON file
    with open(documents_file, 'w') as f:
        json.dump(documents_dict, f)

# Generate embeddings for the web content
embeddings = OpenAIEmbeddings()
vector_store = Chroma.from_documents(documents, embeddings)

# Set up the retriever and QA chain
retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4o-mini"), 
    chain_type="stuff", 
    retriever=retriever,
    return_source_documents=True
)

# Function to handle user queries
def ask_chatbot(query):
    result = qa_chain.invoke({"query": query})
    answer = result["result"]
    sources = result["source_documents"]
    return answer, sources

# Example usage
response, source_docs = ask_chatbot("Give me 5 fun facts about Missouri")
print("Response:", response)
print("Source Docs:", source_docs)
