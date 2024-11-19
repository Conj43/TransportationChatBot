
# langchain imports
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools import StructuredTool


def create_tools(con):
    allowed_tables = ["crashes_2012_2022", "traffic_index_geo2"]
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
        try:
            return str(allowed_tables)
        except Exception:
            return "Error, please try a different query"

    def get_schema(table_name):
        if table_name not in allowed_tables:
            return f"Error: {table_name} is not an allowed table."

        query = f"SHOW CREATE TABLE {table_name};"
        top_3 = f"SELECT * FROM {table_name} LIMIT 3"
        schema_result = "Error Please try again"
        top_3_result = "Error Please try again"
        try:
            with con.cursor() as cursor:
                cursor.execute(query)
                schema = cursor.fetchall()
                schema_result = str(schema)
            with con.cursor() as cursor:
                cursor.execute(top_3)
                top_rows = cursor.fetchall()
                top_3_result = str(top_rows)
            return "Table Schema: " + schema_result + "\nTop 3 Rows: " + top_3_result
        except Exception:
            return "Error, please try a different query"

    def execute_query(query, table_name):
        if table_name not in allowed_tables:
            return f"Error: {table_name} is not an allowed table."

        try:
            with con.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchall()
                return str(result)
        except Exception:
            return "Error, please try a different query"

    list_tables_tool = StructuredTool.from_function(
        func=list_tables,
        name="list_tables_tool",
        description="Use this tool to list all tables in the database",
    )
    get_schema_tool = StructuredTool.from_function(
        func=get_schema,
        name="get_schema_tool",
        description="Use this tool to get the schema for one table in the database",
    )
    query_tool = StructuredTool.from_function(
        func=execute_query,
        name="query_tool",
        description="Use this tool to execute a SQL query as a string. Input the query and the table name you want to query from.",
    )

    tools = [list_tables_tool, get_schema_tool, query_tool, ridsi_tool]
    
    return tools
