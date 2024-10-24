# main file is main.py
# streamlit run main.py --server.maxUploadSize 400


# imports 
from typing import Annotated
import inspect, sqlite3, tempfile, os, re, requests
import streamlit as st
import pandas as pd
from typing import Callable, TypeVar
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from streamlit.delta_generator import DeltaGenerator
from typing_extensions import TypedDict

# langchian imports
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import StreamlitCallbackHandler

# langgraph imports
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver





def call_graph(user_input, config, graph):
    response = graph.invoke({"messages": [("user", user_input)]}, config=config)
    return response["messages"][-1].content



# function to get around streamlit callback handler
T = TypeVar('T')

def get_streamlit_cb(parent_container: DeltaGenerator):
    def decor(fn: Callable[..., T]) -> Callable[..., T]:
        ctx = get_script_run_ctx()
        def wrapper(*args, **kwargs) -> T:
            add_script_run_ctx(ctx=ctx)
            return fn(*args, **kwargs)
        return wrapper

    st_cb = StreamlitCallbackHandler(parent_container=parent_container)

    for name, fn in inspect.getmembers(st_cb, predicate=inspect.ismethod):
        if name.startswith('on_'):
            setattr(st_cb, name, decor(fn))

    return st_cb




# function to create graph, pass in system message and tools for graph
def create_graph(system_message, tools):

    memory = MemorySaver() # initalize memory (State Memory)

    # define class for the state
    class State(TypedDict):
        messages: Annotated[list, add_messages]
    
    graph_builder = StateGraph(State)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) # define llm
    tools = tools # set tools equal to tools
    llm_with_tools = llm.bind_tools(tools) # bind tools to llm
    
    system_message = system_message

    def chatbot(state: State):
        messages = [system_message] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # add chatbot node
    graph_builder.add_node("chatbot", chatbot)

    # create tools node
    tool_node = ToolNode(tools=tools)

    # add tools node
    graph_builder.add_node("tools", tool_node)

    # add conditional edges
    graph_builder.add_conditional_edges("chatbot",tools_condition,)

    # add edge from tools to chatbot
    graph_builder.add_edge("tools", "chatbot")

    # make sure graph always starts at chatbot
    graph_builder.set_entry_point("chatbot")

    # compile graph
    graph = graph_builder.compile(checkpointer=memory)

    return graph # return graph







def invoke_titanbot(user_query):
    selected_action = st.session_state.get("selected_action", "Submit") # get the selected action (buttons determine selected action)
    st.session_state.messages.append({"role": "user", "content": user_query, "image": None, "file_data": None, "filename": None, "html": None}) # add message to history to display
    st.chat_message("user", avatar="💬").write(user_query)
    
    with st.chat_message("assistant", avatar="🤖"):
        st_cb = get_streamlit_cb(st.container()) # modified function to define callbacks using langgraph
        config = {"configurable": {"thread_id": "1"}, "callbacks": [st_cb]} # set the config using thread id and callbacks to dispay to streamlit container
        modified_query = get_selected_action(user_query, selected_action) # depending on selected action, we will modify the query to help narrow focus
        response = call_graph(modified_query, config, st.session_state.get("graph")) # invoke the graph
        last_message = st.session_state.messages[-1] # check if this message display a png or image
        if last_message.get("image"):
            last_message["role"] = "assistant" # we need to redefine role and content if we have an image because we create the message in tools.py in graph_tool
            last_message["content"] = response
        elif last_message.get("file_data"):
            last_message["role"] = "assistant" # we need to redefine role and content if we have a button because we create the message in tools.py in csv_tool
            last_message["content"] = response
        elif last_message.get("html"):
            last_message["role"] = "assistant" # we need to redefine role and content if we have a button because we create the message in tools.py in map_tool
            last_message["content"] = response
        else:
            st.session_state.messages.append({"role": "assistant", "content": response, "image": None, "file_data": None, "filename": None, "html": None}) # if there is no png, or image just keep image as none
        st.write(response) # write response to screen

    st.session_state["selected_action"] = None # reset selected action







def create_db_from_uploaded_csv(uploaded_csv_files):
    # create a temporary SQLite database file
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db_file_path = temp_db_file.name
    temp_db_file.close()

    try:
        with sqlite3.connect(temp_db_file_path) as conn:
            for uploaded_csv_file in uploaded_csv_files:
                if uploaded_csv_file.type == 'text/csv':
                    # read CSV file into pandas DataFrame
                    df = pd.read_csv(uploaded_csv_file)
                    df.columns = df.columns.str.replace(' ', '_')  # replace spaces in column names with underscores

                    # Create table and insert data
                    table_name = os.path.splitext(uploaded_csv_file.name)[0]
                    new_table_name = re.sub(r'\W|^(?=\d)', '_', table_name)
                    df.to_sql(new_table_name, conn, if_exists='replace', index=False)
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    return temp_db_file_path






# function to fetch data from URL and save as SQLite .db file
def fetch_data_and_create_db(url, db_file_path):
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()

        # assuming data['active'] is a list of dictionaries
        if 'active' in data:
            sample_row = data['active'][0]
            columns = sample_row.keys()

            # create table dynamically
            column_definitions = ', '.join([f"{col} TEXT" for col in columns])
            create_table_sql = f"CREATE TABLE IF NOT EXISTS traffic_data ({column_definitions})"
            cursor.execute(create_table_sql)

            # insert data dynamically
            for row in data['active']:
                columns = ', '.join(row.keys())
                placeholders = ', '.join(['?'] * len(row))
                sql = f"INSERT INTO traffic_data ({columns}) VALUES ({placeholders})"
                cursor.execute(sql, list(row.values()))

            conn.commit()
            conn.close()
            return db_file_path
        else:
            st.sidebar.error("Error: JSON does not contain 'active' key.")
            return None
    else:
        st.sidebar.error(f"Error: Unable to fetch data from URL. Status code: {response.status_code}")
        return None
    



# modify user query based on current selected action
def get_selected_action(user_query, selected_action):
    if selected_action == "Code Gen": # tell titanbot to make code
        return "First look at the schema for all tables in this database. Then write a python code to accomplish the following: " + user_query + " This math \
            should be calculated in the python code, do not try to make calculations in your sql query.\
                Only save to a csv file if the output is too long to print. Then show me the code you generate. \
                Don't output the schema. Make sure you save figures, plots or csv files in the code. Use plotly to create graphs and folium to create maps and save them as\
                     html files. DO NOT save multiple files in one code."
    
    elif selected_action == "SQL Query": # tell titanbot to perform sql operations
        return "First look at the schema for all tables in this database. Then generate a sql query to answer this input from the user: " + user_query  + " Then run the query \
            you generated and tell me the results."
    
    elif selected_action == "Run Code": # tell TitanBot to execute code
        return "Use the most recent code and input it into the correct tool to be run. graph_tool is used when the code saves a png image. \
            map_tool is used when the code saves a html file. csv_tool is used when the code saves a csv file. \
                If there are no files saved in the code, you may use code executor. Never run code using a filename that has already been run. \
                    Never save multiple files in one code."
    
    elif selected_action == "Simple Chat": # no modification
        return user_query
    
    else:
        return user_query # no modification





