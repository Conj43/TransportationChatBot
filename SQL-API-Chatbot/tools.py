# main file is main.py

# imports
import os, io, csv,ast
from typing import List
from io import BytesIO


# langchain imports
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel
from langchain.tools import StructuredTool
from langchain_core.messages import SystemMessage, HumanMessage

from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter







# function to initialize tools the agent will use
def create_tools(db_path):


    file_path = "RIDSI-Manual.pdf"
    loader = PyPDFLoader(file_path)

    docs = loader.load()


    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    vectorstore = InMemoryVectorStore.from_documents(
        documents=splits, embedding=OpenAIEmbeddings()
    )
    retriever = vectorstore.as_retriever()



    ridsi_tool = create_retriever_tool(
        retriever,
        "RIDSI-Manual",
        "Searches and returns excerpts from the RIDSI Manual.",
    )


    # initalize sql tools including schema, list tables, query checker and query executor
    db = SQLDatabase.from_uri(f'sqlite:///{db_path}')
    toolkit = SQLDatabaseToolkit(db=db, llm=ChatOpenAI(model="gpt-4o-mini"))
    tools = toolkit.get_tools()

    list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
    get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")
    query_tool = next(tool for tool in tools if tool.name == "sql_db_query")
    checker_tool = next(tool for tool in tools if tool.name == "sql_db_query_checker")



    # create our list of tools
    tools = [list_tables_tool, get_schema_tool, query_tool, 
             checker_tool, ridsi_tool]
    
    # return list of tools that agent can use
    return tools









