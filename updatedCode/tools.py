# main file is main.py

# imports
import sqlite3
from typing import Optional

# langchain imports
from langchain.agents import Tool
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.agents.agent_toolkits import create_retriever_tool


# imports from other files
from utils import collect_text_column_values
from constants import DESCRIPTION



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
        description=DESCRIPTION,
    )

    # create a list of tools, so if we want to add more it will be easier
    tools = [
        Tool(
            name="search_distinct_text",
            func=retriever_tool,
            description=DESCRIPTION
        )
    ]
    # return list of tools that agent can use
    return tools


# defines a class that classifies output from our sql agent as coordinates or not coordinates, we use structured output to easily identify our cases
class Map(BaseModel):
    """Determine whether the input has coordinates and needs to be mapped.""" # instructions for llm
    map: bool = Field(description="If the input includes coordinates or not.") # true if there are coordinates, false if not
    coordinates: Optional[list] = Field(description="List of coordinates, if there are coordinates. Each coordinate entry needs a latitude and longitude.") # list of coordinates if there are any, None if not

# function that creates map llm and returns it
def create_map_llm():
    llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    map_llm = llm.with_structured_output(Map)
    return map_llm
