# imports



# langchain imports
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter





def create_tools():

    file_path = "Postdoc-Handbook.pdf"
    loader = PyPDFLoader(file_path)

    docs = loader.load()


    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    vectorstore = InMemoryVectorStore.from_documents(
        documents=splits, embedding=OpenAIEmbeddings()
    )
    retriever = vectorstore.as_retriever()



    tool = create_retriever_tool(
        retriever,
        "retriever_tool",
        "Searches and returns excerpts from the Missouri Postdoc Handbook.",
    )
    tools = [tool]

    return tools

