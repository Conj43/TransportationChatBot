# # main file is main.py

# # imports
# import os, io, csv,ast
# from typing import List
# from io import BytesIO


# # langchain imports
# from langchain_community.agent_toolkits import SQLDatabaseToolkit
# from langchain_community.utilities.sql_database import SQLDatabase
# from langchain_openai import ChatOpenAI


# from langchain_community.document_loaders import PyPDFLoader
# from langchain_openai import OpenAIEmbeddings
# from langchain.tools.retriever import create_retriever_tool
# from langchain_core.vectorstores import InMemoryVectorStore
# from langchain_text_splitters import RecursiveCharacterTextSplitter

# from heavyai import connect
# import pandas as pd





# # function to initialize tools the agent will use
# def create_tools(heavy_user, heavy_password, heavy_host, heavy_port, heavy_dbname, heavy_protocol):


#     file_path = "RIDSI-Manual.pdf"
#     loader = PyPDFLoader(file_path)

#     docs = loader.load()


#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
#     splits = text_splitter.split_documents(docs)
#     vectorstore = InMemoryVectorStore.from_documents(
#         documents=splits, embedding=OpenAIEmbeddings()
#     )
#     retriever = vectorstore.as_retriever()



#     ridsi_tool = create_retriever_tool(
#         retriever,
#         "RIDSI-Manual",
#         "Searches and returns excerpts from the RIDSI Manual.",
#     )

#     con = connect(user=heavy_user, password=heavy_password, host=heavy_host, port=heavy_port, dbname=heavy_dbname, protocol=heavy_protocol)
#     # initalize sql tools including schema, list tables, query checker and query executor
#     db = SQLDatabase(engine=con)
#     toolkit = SQLDatabaseToolkit(db=db, llm=ChatOpenAI(model="gpt-4o-mini"))
#     tools = toolkit.get_tools()

#     list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
#     get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")
#     query_tool = next(tool for tool in tools if tool.name == "sql_db_query")
#     checker_tool = next(tool for tool in tools if tool.name == "sql_db_query_checker")



#     # create our list of tools
#     tools = [list_tables_tool, get_schema_tool, query_tool, 
#              checker_tool, ridsi_tool]
    
#     # return list of tools that agent can use
#     return tools


import os, io, csv, ast
from typing import List
from io import BytesIO

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools import StructuredTool



import pandas as pd



def create_tools(con):
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


    def list_tables():
        query = "SHOW TABLES;"
        
        try:
            with con.cursor() as cursor:
                cursor.execute(query)
                tables = cursor.fetchall() 
                print("Tables fetched:", tables)
            
           
            
            return str(tables) 
            
        except Exception as e:
            print("Error executing query:", e) 
            return str(e)  



    def get_schema(table_name):
        query = f"SHOW CREATE TABLE {table_name};"

        try:
            with con.cursor() as cursor:
                cursor.execute(query)
                schema = cursor.fetchall() 
                print("schema:", schema)
            
           
            
            return str(schema)  
            
        except Exception as e:
            print("Error executing query:", e) 
            return str(e) 



    def execute_query(query):
        try:

            with con.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchall()  
                print("result:", result)
            
           
            
            return str(result) 
            
        except Exception as e:
            print("Error executing query:", e)  
            return str(e)  


    list_tables_tool = StructuredTool.from_function(
        func=list_tables,
        name="list_tables_tool",
        description="Use this tool to list all tables in the database",
    )
    get_schema_tool = StructuredTool.from_function(
        func=get_schema,
        name="get_schema_tool",
        description="Use this tool to get the schema for specific tables in the database",
    )
    query_tool = StructuredTool.from_function(
        func=execute_query,
        name="query_tool",
        description="Use this tool to execute a SQL query as a string",
    )

    tools = [list_tables_tool, get_schema_tool, query_tool, ridsi_tool]
    
    return tools








