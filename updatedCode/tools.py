# main file is main.py

# imports
import sqlite3
from typing import List, Any, Optional
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static


# langchain imports
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain.tools import StructuredTool

# imports from other files
from utils import collect_text_column_values
from constants import DESCRIPTION_RETRIEVER



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
    def display_map(input):
        map_llm = create_map_llm()
        test = map_llm.invoke(str(input)) # invoke map llm to interpret response
        if test.coordinates and test.map: # coordinates should be a list of coordinates and map should be true
            # using folium map
            m = folium.Map(location=test.coordinates[0], zoom_start=10) # create map and center point
            for coord in test.coordinates: 
                folium.Marker(location=coord).add_to(m) # add each point to the map
            folium_static(m) # display map to the screen

            # using streamlit built in map
            # df = pd.DataFrame(test.coordinates, columns=['latitude', 'longitude']) # convert to pandas df
            # st.map(df) # output map using coordinates to plot
            return "Map displayed successfully."
        else: # return that there were no coordinates to display if coordinates is empty
            return "No coordinates to display."


    # define tool that agent can use to map
    map_tool = StructuredTool.from_function(
        func=display_map,
        name="map_tool",
        description="Use this tool when your query outputs coordinates. \
            Inputs to map tool should be a list of coordinates in the format (latitidue, longitude), (latitidue, longitude)...",
    )

    # function to plot a bar graph
    def plot_graph(input):
        graph_llm = create_graph_llm() # create graph llm to interpret data
        output = graph_llm.invoke(str(input))
        if output.graph: # if llm believes this can be graphed
            df = pd.DataFrame({output.x_axis: output.x_values, output.y_axis: output.y_values})  # define a df using x and y axis
            st.write(f"## {output.plot_title}") # write the title
            st.bar_chart(data=df, x=output.x_axis, y=output.y_axis) # create the chart with corresponding data, x axis and y axis
            st.write(f"### Description") # write the description of the graph
            return "Graph created successfully."
        else:
            st.write("This output does not need to be graphed.")
            return "This output does not need to be graphed."

            
    # tool agent can use to create a bar graph
    graph_tool = StructuredTool.from_function(
        func=plot_graph,
        name="graph_tool",
        description="Use this tool when the user asks you to graph something. \
            Inputs to graph tool should be string from agent, including data about \
            graph as well as a short description of the data.",
    )

    # create our list of tools
    tools = [retriever_tool, map_tool, graph_tool]
    # return list of tools that agent can use
    return tools


def print_output(output):
    print(f"Title: {output.plot_title}")
    print(f"X Values: {output.x_values}")
    print(f"Y Values: {output.y_values}")
    print(f"X Axis: {output.x_axis}")
    print(f"Y Axis: {output.y_axis}")
    print(f"Description: {output.description}")


# defines a class that classifies output from our sql agent as coordinates or not coordinates, we use structured output to easily identify our cases
class Map(BaseModel):
    """Take the input coordinates and translate them into a python list. \
        Format of coordinates will be [(latitude, longitude), (latitude, longitude)...].""" # instructions for llm
    map: bool = Field(description="False if there are no coordinates in the input. True if there are coordinates in the input.") # true if there are coordinates, false if not
    coordinates: Optional[List] = Field(description="List of coordinates, in the pre-defined format. \
                                                             If there are no coordinates, coordinates will be None.")


# class that allows us to define variables for our graph
class Graph(BaseModel):
    """Use data from agent to map values to correct fields."""
    graph: bool = Field(description="True if this output should be graphed. False if not.")
    x_values: List[Any] = Field(description="X-axis values for the graph.")
    y_values: List[Any] = Field(description="Y-axis values for the graph.")
    plot_title: str = Field(description="Title for the graph.")
    x_axis: str = Field(description="Label for the X-axis.")
    y_axis: str = Field(description="Label for the Y-axis.")
    description: str = Field(description="A long, intuitive description of what the graph is showing.")



# function that creates graph llm and returns it
def create_graph_llm():
    llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    graph_llm = llm.with_structured_output(Graph)
    return graph_llm

# function that creates map llm and returns it
def create_map_llm():
    llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    map_llm = llm.with_structured_output(Map)
    return map_llm
