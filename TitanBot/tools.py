# main file is main.py

# imports
import os, io, csv,ast
from typing import List
import streamlit as st
from tavily import TavilyClient
from PIL import Image
from io import BytesIO


# langchain imports
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel
from langchain.tools import StructuredTool
from langchain_core.messages import SystemMessage, HumanMessage

# imports from other files
from sandbox import AICodeSandbox


# tavily used to help generate reports
# tavily_api_key = os.getenv('TAVILY_API_KEY')


# function to keep file names unique
def get_unique_filename(filename):
    base_filename, file_extension = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    counter = 1

    # modify filename until it is unique
    while filename in st.session_state.used_filenames:
        filename = f"{base_filename}_{counter}.{file_extension}" if file_extension else f"{base_filename}_{counter}"
        counter += 1
    
    # add the unique filename to the set
    st.session_state.used_filenames.add(filename)
    return filename




# function to initialize tools the agent will use
def create_tools(db_path):


    # function to display points to a map
    def display_map(input, filename):
        # same idea as code executor, just parses the packages and code

        
        # define file path for db
        container_file_path = '/your_db.db'

        # define img path
        print(filename)
        map_path = filename

        # get db content in bytes
        db_content = get_database_content(db_path)
        print(input)
        packages = parse_packages(input)
        print("Packages Using Parser: ",packages)
        sandbox = AICodeSandbox(packages=packages)

        
        try:
            # write the db to the sandbox
            sandbox.write_file(container_file_path, db_content)

            # run the code that was input by agent
            result = sandbox.run_code(input)

            print(result)

            # read the file from the sandbox
            map_content = sandbox.read_file(map_path)

            # Display the HTML content in Streamlit
            st.components.v1.html(str(map_content), height=600, scrolling=True)

            # make unique filename
            new_filename = get_unique_filename(filename)

            # create message with the map and file
            st.session_state.messages.append({"role": "set", "content": "set", "image": None, "file_data": None, "filename": new_filename, "html": str(map_content)})
            # create button to download map
            st.download_button(
                label=f"Download {new_filename}",
                data=str(map_content),
                file_name=new_filename,
                mime='text/html'
            )
        finally:
            sandbox.close() # close the sandbox

        return input, result # return code and what the code printed


    # define tool that agent can use to map
    map_tool = StructuredTool.from_function(
        func=display_map,
        name="map_tool",
        description="Use this tool when the code saves a html file. Input the filename and the code to be run.",
    )

# REPORT TOOL is commented out

    # function to generate report
    # def report_gen(info):
    #     llm = ChatOpenAI(model="gpt-4o-mini")
    #     # prompt to help llm generate queries for us
    #     QUERY_PROMPT = """You are a MoDOT employee that is focused on data in Missouri.
    #                 Your job is to generate an informative and reliable report. 
    #                 You will be given the user query, and you must generate a list of search queries that will gather 
    #                 any relevant information. Only generate 3 queries max."""

    #     # use llm to generate queries t get a more focused search
    #     queries = llm.with_structured_output(Queries).invoke([
    #         SystemMessage(content=QUERY_PROMPT),
    #         HumanMessage(info)
    #     ])

    #     # use tavily to find outside info on internet
    #     tavily = TavilyClient()
    #     all_responses = []

    #     # invoke tavily using each of the queries we generated (max of 3)
    #     for query in queries.queries:
    #         # print("query: ", query)
    #         response = tavily.search(query=query, max_results=1)
            
    #         # apped results to a list that keeps track of all results
    #         for r in response['results']:
    #             all_responses.append(r)
    #             # all_responses.append(r['content'])
    #             # print(r['content'])
    #             # print(r)


    #     # use llm to then summarize our list of all results
    #     temp = """You are a MoDOT employee that is focused on data in Missouri.
    #         You just searched for data and here are the search results:\n
    #         {compiled_info}\n
    #         Please compile this information into a formal concise summary.
    #         Here is the user's input for context:\n
    #         {info}\n
    #         Use the URLs given to cite your sources."""

    #     prompt = temp.format(compiled_info=all_responses, info=info)

    #     response = llm.invoke(prompt)
        
    #     # return the summarized info as a report which the agent will use to make a report about the given info
    #     return response.content


    # # tool that generares the report
    # report_tool = StructuredTool.from_function(
    #     func=report_gen,
    #     name="report_tool",
    #     description="Use this tool to generate a report. Input the user query into this tool. \
    #         This tool will retrieve multiple responses and summarize them for you. \
    #             Do not make any changes to the report, display them directly to the user."
    # )

    # function to returns database as bytes to be copied into sandbox
    def get_database_content(file_path):
        with open(file_path, 'rb') as file:
            return file.read()
    
    # function that creates a sandox to execute code generated by agent
    # input is the code that was generated
    def code_exec(input):


        print("Input: ",input)

        # define the file path to be used
        container_file_path = '/your_db.db'

        # get db content as bytes
        db_content = get_database_content(db_path)

        print(input)

        # create sandbox environment, making sure to pass in the list of packages that need to be installed for us to run the code
        packages = parse_packages(input)
        print("Using Parser: ",packages)
        sandbox = AICodeSandbox(packages=packages)

        
        try:
            # write the db file to the sandbox using'your_db.db' and bytes of db files
            sandbox.write_file(container_file_path, db_content)

            # run the code that was input
            result = sandbox.run_code(input)

            print(result)
        finally:
            # make sure the close sandbox to clean up resources
            sandbox.close()

        # return code that was used and the result that was printed by sandbox
        return input, result

    # tool to execute the code
    code_executor = StructuredTool.from_function(
        func=code_exec,
        name="code_executor",
        description="Use this tool to run code that does not save a file. The code should print the output. Input the code into this tool to be executed."
    )

    
    # function used to run code and display a graph
    def new_graph_func(input, filename):
        # same idea as code executor, just parses the packages and code

        
        # define file path for db
        container_file_path = '/your_db.db'

        # define img path
        img_path = filename

        # get db content in bytes
        db_content = get_database_content(db_path)
        print(input)
        packages = parse_packages(input)
        print("Using Parser: ",packages)
        sandbox = AICodeSandbox(packages=packages)


        try:
            # write the db to the sandbox
            sandbox.write_file(container_file_path, db_content)

            # run the code that was input by agent
            result = sandbox.run_code(input)

            print(result)

            # read the file from the sandbox
            plot_image = sandbox.read_file(img_path)

            
            img = Image.open(BytesIO(plot_image))
            st.session_state.messages.append({"role": "set", "content": "set", "image": img, "file_data": None, "filename": None, "html": None}) # create new message with image, the role and content will be set later
            st.image(img) # display image
        finally:
            sandbox.close() # close the sandbox

        return input, result # return code and what the code printed

    # graphing tool that llm has access to
    graph_tool = StructuredTool.from_function(
        func=new_graph_func,
        name="graph_tool",
        description="Use this tool when the code saves a png image. Input code to create an image and the file name of the image."
    )


    # function to save data to csv file and allow users to download it
    def csv_func(input, filename):
        # same idea as other functions to parse packages and code

        # define path for db in sandbox
        container_file_path = '/your_db.db'

        # put db content into bytes
        db_content = get_database_content(db_path)
        print(input)
        packages = parse_packages(input)
        print("Using Parser: ",packages)
        sandbox = AICodeSandbox(packages=packages)


        try:
            # write the db file to the sandbox
            sandbox.write_file(container_file_path, db_content)

            # run the code in the sandbox
            result = sandbox.run_code(input)

            print(result)

            # read csv from sandbox
            data = sandbox.read_file(filename)

            # prepare csv data for inputting the values into the button
            csv_data = io.StringIO()
            csv_writer = csv.writer(csv_data)
            csv_writer.writerows(data)
            csv_data.seek(0) 

 
            # create button to download csv 
            new_filename = get_unique_filename(filename)


            st.download_button(
                label=f"Download {new_filename}",
                data=csv_data.getvalue(),
                file_name=new_filename,
                mime='text/csv'
            )
            st.session_state.messages.append({"role": "set", "content": "set", "image": None, "file_data": csv_data.getvalue(), "filename": new_filename, "html": None}) # create new message with btn, the role and content will be set later
        finally:
            # make sure to close sandbox
            sandbox.close()

        # return code and printed result of code
        return input, result

    # csv tool
    csv_tool = StructuredTool.from_function(
        func=csv_func,
        name="csv_tool",
        description="Use this tool when the code saves a csv file. Input code to create a csv file. Input name for csv file used in code."
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
    tools = [map_tool, list_tables_tool, get_schema_tool, query_tool, 
             checker_tool, code_executor, graph_tool, csv_tool]
    
    # return list of tools that agent can use
    return tools


# use AST to parse packages
def parse_packages(code):
    excluded_packages = {"sqlite3", "json", "os", "math", "datetime", "random", "sys"} # these are installed with python, or they are ones we dont want to use
    package_set = set()

    def get_top_level_package(package_name): # like for matplotlib.pyplot we just need to download matplotlib
        return package_name.split('.')[0]

    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    package_set.add(get_top_level_package(alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module:  # ensure there is a module
                    package_set.add(get_top_level_package(node.module))
    except SyntaxError as e:
        print(f"Syntax error in code: {e}")

    # exclude the specified packages
    packages = [pkg for pkg in package_set if pkg not in excluded_packages]
    
    return packages




# class Queries(BaseModel):
#     queries: List[str]



