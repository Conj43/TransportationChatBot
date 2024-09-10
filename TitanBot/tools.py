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
from geopy.distance import geodesic
import matplotlib as plt
from tavily import TavilyClient
import os
from PIL import Image


# langchain imports
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.tools import StructuredTool
from langchain_core.messages import SystemMessage, HumanMessage

# imports from other files
from calculations import prep_data, arterial_speed_index, calculate_arterial
from sandbox import AICodeSandbox
from utils import create_graph, call_graph



tavily_api_key = os.getenv('TAVILY_API_KEY')

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


    def tti_calculator(query,batch_size=200):
        try:

            # code to use batching is in comments


            conn = sqlite3.connect(db_path)
            # offset = 0
            # dfs = []
            # while True:
            #     batch_query = f"{query} LIMIT {batch_size} OFFSET {offset}"
            #     df_batch = pd.read_sql_query(batch_query, conn)
            #     if df_batch.empty:
            #         break
            #     dfs.append(df_batch)
            #     offset += batch_size
            
            df = pd.read_sql_query(query, conn)
            conn.close()
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
        description="Use this tool to calculate the Travel Time Index(TTI). The user will ask you to calculate tti, \
            so you will generate the correct query and input it into this tool. The query you create should query \
                for all data in the correct table. Make sure your calculations are rounded to 5 decimal places."
    )




    def speed_index_calculator(input):
        # try:
        #     tools = create_code_tools(db_path)
        #     code_graph = create_graph(SI_CODE_SYSTEM_MESSAGE, tools)
        #     config = {"configurable": {"thread_id": "2"}}
        #     response = call_graph(input, config, code_graph)
        #     print("CodeCC: ",response)
        #     code, result = code_exec(response)
        #     value = f"Code: {code}\n Result: {result}"
        #     return value
        # except:
        #     print('error')

        # return "Error"
        return 0

    speed_index_tool = StructuredTool.from_function(
        func=speed_index_calculator,
        name="speed_index_tool",
        description="Use this tool to calculate speed index. Input is a string explaning the user's request.  \
                You will get the code and the result of executing the code.  \
                Display the code to the user to show them how you got your results, then show them your results."
    )


    def congestion_map(query, batch_size=1000):
        try:
            conn = sqlite3.connect(db_path)
            # Execute the query and process the data
            df = pd.read_sql_query(query, conn)
            conn.close()
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
        description="Use this tool to draw a congestion map. The user will ask you to make a congestion map, \
            so you will generate the correct query and input it into this tool. The query you create should query \
                for all data in the correct table. After the map is created use the report_tool to generate an informative \
                    report on the data in the map."
    )

    def congestion_level(query, batch_size=1000):
        try:
            conn = sqlite3.connect(db_path)
            # Execute the query and process the data
            df = pd.read_sql_query(query, conn)
            conn.close()
            result_df_edit = prep_data(df)
            total_df = calculate_arterial(result_df_edit)
            
            # Calculate congestion level for each segment
            congestion_df = total_df.groupby(['tmc', 'link', 'start_lat', 'end_lat', 'start_long', 'end_long']).agg({
                "congestion_level": "first"
            }).reset_index()

            return "Successful Query. Here is the congestion level",congestion_df
        
        except sqlite3.Error as e:
            return f"SQL query failed with error: {e} Please use sql_db_schema and then rewrite the query and try again using congestion_level_tool!"
        except Exception as e:
            return f"An unexpected error occurred: {e} Please use sql_db_schema and then rewrite the query and try again using congestion_level_tool!"

    congestion_level_tool = StructuredTool.from_function(
        func=congestion_level,
        name="congestion_level_tool",
        description="Use this tool to calculate the congestion_level. The user will ask you for a calculate the congestion level, \
            so you will generate the correct query and input it into this tool."
    )




    def roadwork_search (query0, query1):
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(query1, conn)
            result_df_edit = prep_data(df)
            total_df = calculate_arterial(result_df_edit)
            conn.close()
            # Calculate congestion level for each segment
            congestion_df = total_df.groupby(['tmc', 'link', 'start_lat', 'end_lat', 'start_long', 'end_long']).agg({
                "congestion_level": "first"
            }).reset_index()


            acc_df = pd.read_sql_query(query0, conn)
            acc_df['dt'] = pd.to_datetime(acc_df['pub_millis'])
            acc_df['year'] = acc_df['dt'].dt.year


            # Function to check if an accident is within a certain radius
            def is_within_range(row, accident_data, radius=1.0):
                start_point = (row['start_lat'], row['start_long'])
                end_point = (row['end_lat'], row['end_long'])
                
                for _, accident in accident_data.iterrows():
                    accident_point = (accident['latitude'], accident['longitude'])
                    if geodesic(start_point, accident_point).miles <= radius or geodesic(end_point, accident_point).miles <= radius:
                        return True
                return False

            # Function to get nearby accident info
            def get_nearby_info(row, accident_data, radius=1.0):
                start_point = (row['start_lat'], row['start_long'])
                end_point = (row['end_lat'], row['end_long'])
                
                nearby_info = []
                for _, accident in accident_data.iterrows():
                    accident_point = (accident['latitude'], accident['longitude'])
                    if geodesic(start_point, accident_point).miles <= radius or geodesic(end_point, accident_point).miles <= radius:
                        nearby_info.append(accident['year'])
                return nearby_info

            # Apply functions to dataframe
            congestion_df['roadwork_nearby'] = congestion_df.apply(is_within_range, axis=1, accident_data=acc_df)
            congestion_df['years'] = congestion_df.apply(lambda row: ', '.join(map(str, get_nearby_info(row, acc_df))) if get_nearby_info(row, acc_df) else 'None', axis=1)

            congestion_df['years'] = congestion_df['years'].apply(lambda x: x.split(',')[0].strip())

            return "Successful Query. Here is the congestion level",congestion_df
        
        except sqlite3.Error as e:
            return f"SQL query failed with error: {e} Please use sql_db_schema and then rewrite the query and try again using roadwork_search_tool!"
        except Exception as e:
            return f"An unexpected error occurred: {e} Please use sql_db_schema and then rewrite the query and try again using roadwork_search_tool!"

    roadwork_search_tool = StructuredTool.from_function(
        func=roadwork_search,
        name="roadwork_search_tool",
        description="Use this tool to determine if there was roadwork in a given year. The user will ask you for a determine the roadwork, \
            so you will generate the correct query and input it into this tool."
    )

    def fatality_yearly_comparison(query, batch_size=1000):
        try:
            # Execute the query and process the data
            #query ="SELECT * FROM accidents" 
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            #Preprocess the Data
            df['ACTIVATION'] = pd.to_datetime(df['ACTIVATION'])
            df['year'] = df['ACTIVATION'].dt.year
            df['quarter'] = df['ACTIVATION'].dt.quarter

            # Count the number of incidents per year and quarter
            count_data = df.groupby(['year', 'quarter', 'ACC_SVRTY_']).size().unstack(fill_value=0).reset_index()

            fatal_counts = count_data.pivot(index='year', columns='quarter', values='FATAL').fillna(0)
            injury_counts = count_data.pivot(index='year', columns='quarter', values='DISABLING INJURY').fillna(0)

            # Calculate the 5-year average for fatal (you can also do this for injury if needed)
            five_year_average = fatal_counts.mean(axis=1)

            #Plot the Data
            fig, ax = plt.subplots(figsize=(10, 6))

            # Plot each quarter as a separate stacked bar for fatal counts
            quarters = ['1st Qtr', '2nd Qtr', '3rd Qtr', '4th Qtr']
            colors = ['#4c78a8', '#f58518', '#54a24b', '#e45756']

            for i, quarter in enumerate(fatal_counts.columns, start=1):
                ax.bar(fatal_counts.index, fatal_counts[quarter], color=colors[i-1], label=f'Q{i}')

            # Plot the 5-year average as a line
            # ax.plot(fatal_counts.index, five_year_average, color='blue', marker='o', linestyle='-', linewidth=2, label='5-year average')


            # Add labels, title, and legend
            ax.set_xlabel('Calendar Year')
            ax.set_ylabel('Number of Fatalities')
            ax.set_title('Number of Fatalities')
            ax.legend(loc='upper right')

            st.pyplot(plt.gcf()) # instead of plt.show()
            # plt.show()


            return "Fatalities graph displayed successfully", fatal_counts

        except sqlite3.Error as e:
            return f"SQL query failed with error: {e} Please use sql_db_schema and then rewrite the query and try again using fatality_yearly_comparison_tool!"
        except Exception as e:
            return f"An unexpected error occurred: {e} Please use sql_db_schema and then rewrite the query and try again using fatality_yearly_comparison_tool!"

    fatality_yearly_comparison_tool = StructuredTool.from_function(
        func=fatality_yearly_comparison,
        name="fatality_yearly_comparison_tool",
        description="Use this tool to calculate the comparison of the quarterly fatalities. The user will ask you for to compare the previous year's fatalities , \
            so you will generate the correct query and input it into this tool. Query for all data from the correct table."
    )

    def report_gen(info):
        llm = ChatOpenAI(model="gpt-4o-mini")
        QUERY_PROMPT = """You are a MoDOT employee that is focused on data in Missouri.
                    Your job is to generate an informative and reliable report. 
                    You will be given the user query, and you must generate a list of search queries that will gather 
                    any relevant information. Only generate 3 queries max."""

        queries = llm.with_structured_output(Queries).invoke([
            SystemMessage(content=QUERY_PROMPT),
            HumanMessage(info)
        ])
        tavily = TavilyClient()
        all_responses = []

        for query in queries.queries:
            # print("query: ", query)
            response = tavily.search(query=query, max_results=1)
            
            for r in response['results']:
                all_responses.append(r)
                # all_responses.append(r['content'])
                # print(r['content'])
                # print(r)

        temp = """You are a MoDOT employee that is focused on data in Missouri.
            You just searched for data and here are the search results:\n
            {compiled_info}\n
            Please compile this information into a formal concise summary.
            Here is the user's input for context:\n
            {info}\n
            Use the URLs given to cite your sources."""

        prompt = temp.format(compiled_info=all_responses, info=info)

        response = llm.invoke(prompt)
        
        return response.content



    report_tool = StructuredTool.from_function(
        func=report_gen,
        name="report_tool",
        description="Use this tool to generate a report. Input the user query into this tool. \
            This tool will retrieve multiple responses and summarize them for you. \
                Do not make any changes to the report, display them directly to the user."
    )


    def get_database_content(file_path):
        with open(file_path, 'rb') as file:
            return file.read()
    
    def code_exec(input):
        llm=ChatOpenAI(model="gpt-4o-mini", temperature=0)
        code_llm = llm.with_structured_output(Code)
        response=code_llm.invoke(input)
        print("Input: ",input)
        
        container_file_path = '/your_db.db'
        print("dbpath: ",db_path)
        db_content = get_database_content(db_path)
        print("container file path: ",container_file_path)
        print("Dependencies: ", response.dependencies)
        sandbox = AICodeSandbox(packages=response.dependencies)
        print("Code: ", response.code)
        
        try:
            sandbox.write_file(container_file_path, db_content)
            result = sandbox.run_code(response.code)
            print(result)
        finally:
            sandbox.close()

        return response.code, result


    code_executor = StructuredTool.from_function(
        func=code_exec,
        name="code_executor",
        description="Use this tool when you are asked to execute or run code generated by the Agent.\
              Input a list of the required dependencies, \
                and the python script that needs to be run into this tool. Make sure your input is a string. \
                You will run the code and return the code and output. Display the code and the result to the user. \
                      Ask if they would like to make any changes to it."
    )



    def clean_file(file_path):
        with open(file_path, 'rb') as file:
            data = file.read()
        
        # Find the start of the PNG file signature
        png_signature = b'\x89PNG\r\n\x1a\n'
        start_index = data.find(png_signature)
        
        if start_index != -1:
            # Trim the data to start at the PNG signature
            cleaned_data = data[start_index:]
            with open(file_path, 'wb') as file:
                file.write(cleaned_data)
        else:
            raise ValueError("PNG signature not found in file")
    

    def new_graph_func(input):
        llm=ChatOpenAI(model="gpt-4o-mini", temperature=0)
        code_llm = llm.with_structured_output(Code)
        response=code_llm.invoke(input)
        
        container_file_path = '/your_db.db'
        db_content = get_database_content(db_path)
        print("Dependencies: ", response.dependencies)
        sandbox = AICodeSandbox(packages=response.dependencies)
        print("Code: ", response.code)
        
        try:
            sandbox.write_file(container_file_path, db_content)
            result = sandbox.run_code(response.code)
            print(result)
            plot_image = sandbox.read_file('/new.png')
            with open('new.png', 'wb') as file:
                file.write(plot_image)
            print("Plot saved as new.png")

            # clean file
            clean_file('new.png')

        
            img_path = 'new.png'
            img = Image.open(img_path)
            st.write(img)
        finally:
            sandbox.close()

        return response.code, result


    graph_tool = StructuredTool.from_function(
        func=new_graph_func,
        name="graph_tool",
        description="Use this tool when you are asked to run graph tool. Input code to create a graph."
    )



    db = SQLDatabase.from_uri(f'sqlite:///{db_path}')
    toolkit = SQLDatabaseToolkit(db=db, llm=ChatOpenAI(model="gpt-4o-mini"))
    tools = toolkit.get_tools()

    list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
    get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")
    query_tool = next(tool for tool in tools if tool.name == "sql_db_query")
    checker_tool = next(tool for tool in tools if tool.name == "sql_db_query_checker")



    # create our list of tools
    tools = [map_tool, speed_index_tool, tti_tool, congestion_map_tool, congestion_level_tool, 
             list_tables_tool, get_schema_tool, query_tool, checker_tool, fatality_yearly_comparison_tool, 
             roadwork_search_tool, report_tool, code_executor, graph_tool]
    
    # return list of tools that agent can use
    return tools


def create_code_tools(db_path):
    db = SQLDatabase.from_uri(f'sqlite:///{db_path}')
    toolkit = SQLDatabaseToolkit(db=db, llm=ChatOpenAI(model="gpt-4o-mini"))
    tools = toolkit.get_tools()

    list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
    get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")

    tools = [list_tables_tool, get_schema_tool]
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


# class that allows us to define variables for our code execution
class Code(BaseModel):
    """Correctly map dependencies that need to be installed."""
    dependencies: Optional[List[str]] = Field(description="List of dependencies to be installed. sqlite and sqlite3 are already installed, DO NOT include in this list.")
    code: str = Field(description="Put the python code into this field.")




# function that creates map llm and returns it
def create_map_llm():
    llm=ChatOpenAI(model="gpt-4o-mini", temperature=0)
    map_llm = llm.with_structured_output(Map)
    return map_llm

class Queries(BaseModel):
    queries: List[str]



