# main file is main.py

# imports
import sqlite3
from typing import Optional
import pandas as pd
import streamlit as st

# langchain imports
from langchain.agents import Tool
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.tools import QuerySQLCheckerTool
from langchain.tools import tool, StructuredTool

# imports from other files
from utils import collect_text_column_values
from constants import DESCRIPTION_RETRIEVER, DESCRIPTION_CHECKER







# function to initialize tools the agent will use
def create_tools(db_path):
    conn = sqlite3.connect(db_path) # use db path parameter to crate connection to the selected database
    text_values = collect_text_column_values(conn) # run function from utils.py to get all disctinct text values
    conn.close() # close connection

    # initialzie a vector db that will embed all the distict text values
    vector_db = FAISS.from_texts(text_values, OpenAIEmbeddings())

    # retriever will be able to retrieve k most similar embeddings and convert to our text values they correspond to
    retriever = vector_db.as_retriever(search_kwargs={"k": 5})

    # initilaize retriever tool 
    retriever_tool = create_retriever_tool(
        retriever,
        name="search_distinct_text",
        description=DESCRIPTION_RETRIEVER,
    )

    # function to display points to a map using streamlit's st.map
    def display_map(input: str):
        map_llm = create_map_llm()
        test = map_llm.invoke(input) # invoke map llm to interpret response
        if test.coordinates and test.map: # coordinates should be a list of coordinates
            df = pd.DataFrame(test.coordinates, columns=['latitude', 'longitude']) # convert to pandas df
            st.map(df) # output map using coordinates to plot
            return "Map displayed successfully."
        else: # write that there were no coordinates to display if coordinates is empty
            return "No coordinates to display."



    map_tool = StructuredTool.from_function(
        func=display_map,
        name="map_tool",
        description="Use this tool when your query outputs coordinates. \
            Inputs to map tool should be a list of coordinates in the format (latitidue, longitude), (latitidue, longitude)...",
    )
    # query_check_tool = QuerySQLCheckerTool

    # create a list of tools, so if we want to add more it will be easier
    tools = [retriever_tool, map_tool]
    # return list of tools that agent can use
    return tools


# defines a class that classifies output from our sql agent as coordinates or not coordinates, we use structured output to easily identify our cases
class Map(BaseModel):
    """Determine whether the input has coordinates. If there are no coordinates, map should be false.""" # instructions for llm
    map: bool = Field(description="False if there are no coordinates in the input. True if there are coordinates in the input.") # true if there are coordinates, false if not
    coordinates: Optional[list] = Field(description="List of coordinates, if there are coordinates. Each coordinate entry needs a latitude and longitude.") # list of coordinates if there are any, None if not

# function that creates map llm and returns it
def create_map_llm():
    llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    map_llm = llm.with_structured_output(Map)
    return map_llm
