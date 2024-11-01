import os
import json
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.documents import Document  # Import Document class
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access USER_AGENT and OpenAI API key
user_agent = os.getenv('LANGCHAIN_USER_AGENT')
openai_api_key = os.getenv('OPENAI_API_KEY')

# Define the file path for loading documents
documents_file = "documents.json"

# Load documents from file
if os.path.exists(documents_file) and os.path.getsize(documents_file) > 0:
    with open(documents_file, 'r') as f:
        documents_dict = json.load(f)  # Load as dictionaries
else:
    print(f"No documents found in {documents_file}. Please run save_documents.py first.")
    exit()

# Convert dictionaries back to Document objects
documents = [Document(page_content=doc['content'], metadata=doc['metadata']) for doc in documents_dict]

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

# Function to handle user queries with a prompt
def ask_chatbot(query):
    # Define a prompt to guide the model's responses
    prompt = f"You are a knowledgeable assistant about Missouri. Answer the following question: {query}"
    
    # Invoke the QA chain with the prompt
    result = qa_chain.invoke({"query": prompt})
    answer = result["result"]
    sources = result["source_documents"]
    return answer, sources

# Example usage
while True:
    user_query = input("Ask a question about Missouri (or type 'exit' to quit): ")
    if user_query.lower() == 'exit':
        break
    response, source_docs = ask_chatbot(user_query)
    print("Response:", response)
    # Optionally print source documents
    # print("Source Docs:", source_docs)
