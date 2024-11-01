import os
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import JSONLoader
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


if "OPENAI_API_KEY" not in os.environ:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")


try:
    json_loader = JSONLoader(file_path="titan_data.json", jq_schema=".", text_content=False)
    documents = json_loader.load()
except Exception as e:
    raise RuntimeError(f"Failed to load JSON data: {e}")


embeddings = OpenAIEmbeddings()  
vector_store = Chroma.from_documents(documents, embeddings)

# 3. Set up the retriever and QA chain
retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4o-mini"), 
    chain_type="stuff", 
    retriever=retriever,
    return_source_documents=True
)


def ask_titanbot(query):
    try:
        result = qa_chain.invoke({"query": query})
        answer = result["result"]
        sources = result["source_documents"]
        
        return answer, sources
    except Exception as e:
        return f"Error during query processing: {e}", []


response, source_docs = ask_titanbot("What data formats does titanbot support?")
print("Response:", response , "\n\n")
print("Source Docs: ", source_docs)
