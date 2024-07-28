# main file is main.py

# imports
import sqlite3
from typing import List, Any, Optional, Tuple
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static
import osmnx as ox
import geopandas as gpd
from shapely.geometry import LineString
import sklearn





# langchain imports
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain.tools import StructuredTool

# imports from other files
from utils import collect_text_column_values, get_all_col_names
from constants import DESCRIPTION_RETRIEVER, DESCRIPTION_COLS
from calculations import prep_data, Calculate_Speed_Index, calculate_freeway, combine_SI_AM_PM, arterial_spped_index, calculate_arterial


# function to initialize tools the agent will use
def create_tools(db_path):
    conn = sqlite3.connect(db_path) # use db path parameter to crate connection to the selected database
    

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
            # st.write(output.description)
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
            graph as well as a short description of the data. Make sure you create the graph\
                  at a zoom fator to where the user can see the differences in values",
    )


    def tti_calculator(query,batch_size=200):
        try:

            # conn = sqlite3.connect(db_path)
            # offset = 0
            # dfs = []
            # while True:
            #     batch_query = f"{query} LIMIT {batch_size} OFFSET {offset}"
            #     df_batch = pd.read_sql_query(batch_query, conn)
            #     if df_batch.empty:
            #         break
            #     dfs.append(df_batch)
            #     offset += batch_size
            # conn.close()
            df = pd.read_sql_query(query, conn)
            # result_df = pd.concat(dfs, ignore_index=True)
            result_df_edit = prep_data(df)
            total_df = calculate_arterial(result_df_edit)
            aggregated_df = total_df.groupby(['tmc', 'link', 'month']).agg({
                        "TTI_mean": "mean"
                    }).reset_index()
            yearly_averages = aggregated_df[['TTI_mean']].mean(skipna=True)

            return "Successful Query", yearly_averages
        
        except sqlite3.Error as e:
            return f"SQL query failed with error: {e} Please use sql_db_schema and then rewrite the query and try again using tti_calculator!"
        except Exception as e:
            return f"An unexpected error occurred: {e} Please rewrite sql_db_schema and then the query and try again using tti_calculator!"

    tti_tool = StructuredTool.from_function(
        func=tti_calculator,
        name="tti_tool",
        description="Use this tool to calculate the Time Travel Index or TTI. The user will ask you to calculate TTI, \
            so you will generate the correct query and input it into this tool."
    )









    def speed_index_calculator(query,batch_size=200):
        try:

            # conn = sqlite3.connect(db_path)
            # offset = 0
            # dfs = []
            # while True:
            #     batch_query = f"{query} LIMIT {batch_size} OFFSET {offset}"
            #     df_batch = pd.read_sql_query(batch_query, conn)
            #     if df_batch.empty:
            #         break
            #     dfs.append(df_batch)
            #     offset += batch_size
            # conn.close()

            # result_df = pd.concat(dfs, ignore_index=True)
            df = pd.read_sql_query(query, conn)
            result_df_edit = prep_data(df)
            
            combined_arterials=arterial_spped_index(result_df_edit)
            aggregated_df = combined_arterials.groupby(['tmc', 'link', 'month']).agg({
                        "SI": "mean",
                        "congestion_level": "first"
                    }).reset_index()
            yearly_averages = aggregated_df[['SI']].mean(skipna=True)
            congestion_level = aggregated_df['congestion_level'].iloc[0]
                
                # Create a DataFrame for the output
            output_df = pd.DataFrame({
                'yearly_averages_SI': [yearly_averages['SI']],
                'congestion_level': [congestion_level]
            })
            return "Successful Query. Here is the SI and congestion level", output_df
        
        except sqlite3.Error as e:
            return f"SQL query failed with error: {e} Please use sql_db_schema and then rewrite the query and try again using speed_index_tool!"
        except Exception as e:
            return f"An unexpected error occurred: {e} Please use sql_db_schema and then rewrite the query and try again using speed_index_tool!"

    speed_index_tool = StructuredTool.from_function(
        func=speed_index_calculator,
        name="speed_index_tool",
        description="Use this tool to calculate the speed index. The user will ask you to calculate speed index, \
            so you will generate the correct query and input it into this tool."
    )


    def congestion_map(query, batch_size=200):
        try:
            # Execute the query and process the data
            df = pd.read_sql_query(query, conn)
            result_df_edit = prep_data(df)
            total_df = calculate_arterial(result_df_edit)
            
            # Calculate congestion level for each segment
            congestion_df = total_df.groupby(['tmc', 'link', 'start_lat', 'end_lat', 'start_long', 'end_long']).agg({
                "SI": "mean",
                "congestion_level": "first"
            }).reset_index()

            # Ensure latitude and longitude are numeric
            congestion_df[['start_lat', 'end_lat', 'start_long', 'end_long']] = congestion_df[['start_lat', 'end_lat', 'start_long', 'end_long']].apply(pd.to_numeric)

            # Define the area of interest
            place_name = "St. Louis, Missouri, USA"  # Change as needed

            # Download road network data for the area
            graph = ox.graph_from_place(place_name, network_type='drive')
            edges = ox.graph_to_gdfs(graph, nodes=False)
            nodes = ox.graph_to_gdfs(graph, edges=False)

            # Convert points to GeoDataFrame
            gdf = gpd.GeoDataFrame(
                congestion_df,
                geometry=gpd.points_from_xy(congestion_df.start_long, congestion_df.start_lat),
                crs='EPSG:4326'
            )

            # Function to get the nearest node in the road network
            def get_nearest_node(lat, long):
                return ox.distance.nearest_nodes(graph, long, lat)

            # Find nearest nodes for start and end points
            congestion_df['start_node'] = congestion_df.apply(lambda row: get_nearest_node(row.start_lat, row.start_long), axis=1)
            congestion_df['end_node'] = congestion_df.apply(lambda row: get_nearest_node(row.end_lat, row.end_long), axis=1)

            # Calculate shortest paths between nodes
            congestion_df['route'] = congestion_df.apply(lambda row: ox.shortest_path(graph, row.start_node, row.end_node, weight='length'), axis=1)
            congestion_df.dropna(subset=['route'], inplace=True)

            # Define color mapping for congestion levels
            color_mapping = {
                "Light": "#83cb22",    # Dark Green
                "Moderate": "#fcff30", # Dark Yellow
                "Heavy": "#f9502b",    # Dark Orange
                "Severe": "#b62000"    # Dark Red
            }

            # Create a Folium map
            m = folium.Map(location=[38.77468, -90.41166], zoom_start=10)

            # Add road segments to the map
            for _, row in congestion_df.iterrows():
                route_nodes = row['route']
                route_coords = [(nodes.loc[node].y, nodes.loc[node].x) for node in route_nodes]
                
                # Create a tooltip with segment and link numbers, and congestion level
                tooltip_text = f"Segment Number: {row['tmc']}<br>Link Number: {row['link']}<br>Congestion Level: {row['congestion_level']}"
                
                folium.PolyLine(
                    locations=route_coords,
                    color=color_mapping[row.congestion_level],
                    weight=5,
                    opacity=0.7,
                    tooltip=folium.Tooltip(tooltip_text, sticky=True)
                ).add_to(m)

            # Display map to the screen
            folium_static(m)

            return "Congestion Map displayed successfully"
        
        except sqlite3.Error as e:
            return f"SQL query failed with error: {e} Please use sql_db_schema and then rewrite the query and try again using congestion_map_tool!"
        except Exception as e:
            return f"An unexpected error occurred: {e} Please use sql_db_schema and then rewrite the query and try again using congestion_map_tool!"

    congestion_map_tool = StructuredTool.from_function(
        func=congestion_map,
        name="congestion_map_tool",
        description="Use this tool to draw the congestion map. The user will ask you for a congestion map, \
            so you will generate the correct query and input it into this tool."
    )



    # create our list of tools
    tools = [map_tool, graph_tool, speed_index_tool, tti_tool, congestion_map_tool]
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
    # """Take the input coordinates and translate it into a list of coordinate pairs in the format: [(21.21323, -83.43232), (43.5435, 54.2344)...] as an example.""" # instructions for llm
    map: bool = Field(description="False if there are no coordinates in the input. True if there are coordinates in the input.") # true if there are coordinates, false if not
    coordinates: Optional[List[Tuple]] = Field(description="List of coordinate pairs. If there are no coordinates, coordinates will be None.")


# class that allows us to define variables for our graph
class Graph(BaseModel):
    """Use data from agent to map values to correct fields."""
    graph: bool = Field(description="True if this output should be graphed. False if not.")
    x_values: List[Any] = Field(description="X-axis values for the graph.")
    y_values: List[Any] = Field(description="Y-axis values for the graph.")
    plot_title: str = Field(description="Title for the graph.")
    x_axis: str = Field(description="Label for the X-axis.")
    y_axis: str = Field(description="Label for the Y-axis.")
    description: str = Field(description="You are a transportation engineer who is giving a high level, informative description of the data in the graph.")



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
