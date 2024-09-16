# to run this application: streamlit run main.py
# streamlit run main.py --server.maxUploadSize 400

# imports
import os, tempfile, requests, sqlite3
from dotenv import load_dotenv
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL


# langchain imports
from langchain_community.utilities.sql_database import SQLDatabase

# imports from other files
from utils import call_graph, get_streamlit_cb, create_graph
from ui import display_chat_messages, get_user_query, setup_streamlit_page, clear_message_history, get_selected_action
from prompts import AGENT_SYSTEM_MESSAGE
from tools import create_tools

# load env variables
load_dotenv()

# define open ai api key
openai_api_key = os.environ['OPENAI_API_KEY']

# sets up streamlit page in ui.py
setup_streamlit_page()

# Initialize session state variables
if "db_path" not in st.session_state:
    st.session_state.db_path = None

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?", "image": None, "file_data": None, "filename": None}]




# Sidebar content
if st.sidebar.button("Clear History"):
    clear_message_history()


# sidebar information
st.sidebar.subheader("Welcome to TitanBot!")
st.sidebar.markdown("First, upload your database with traffic or accident information, then chat with your data! \
                    Use the different buttons to specify what task you'd like TitanBot to perform. Click the button first, \
                    then it will show it has been activated. Then you may submit your query or question, and TitanBot will use \
                    it's tool to best answer your request.")
st.sidebar.markdown("---")
st.sidebar.subheader("Database Upload")
st.sidebar.markdown("Upload a SQLite .db file for analysis.")
uploaded_file = st.sidebar.file_uploader("Choose a database file", key="bottom_uploader")

# upload db
if uploaded_file is not None:
    if uploaded_file.name.endswith('.db'):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.write(uploaded_file.read())
        temp_file_path = temp_file.name
        temp_file.close()
        st.session_state.db_path = temp_file_path
        st.sidebar.success("Database uploaded successfully.") 
    else:
        st.sidebar.error("Error: The uploaded file is not a .db file. Please try a .db file.")

# Function to fetch data from URL and save as SQLite .db file
def fetch_data_and_create_db(url, db_file_path):
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()

        # Assuming data['active'] is a list of dictionaries
        if 'active' in data:
            sample_row = data['active'][0]
            columns = sample_row.keys()

            # Create table dynamically
            column_definitions = ', '.join([f"{col} TEXT" for col in columns])
            create_table_sql = f"CREATE TABLE IF NOT EXISTS traffic_data ({column_definitions})"
            cursor.execute(create_table_sql)

            # Insert data dynamically
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

# Option to input a URL for data
st.sidebar.markdown("Or, provide a URL to fetch data:")
data_url = st.sidebar.text_input("Enter URL")

# Handle URL input
if st.sidebar.button("Fetch Data"):
    if data_url:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file_path = temp_file.name
        temp_file.close()
        db_path = fetch_data_and_create_db(data_url, temp_file_path)
        if db_path:
            st.session_state.db_path = db_path
            st.sidebar.success("Data fetched and database created successfully.")
    else:
        st.sidebar.error("Error: Please provide a valid URL.")

# Initialize db connection to your .db file
if st.session_state.db_path is not None:
    db_url = URL.create( 
        drivername="sqlite",
        database=st.session_state.db_path,
        query={"mode": "ro"} # open in read only mode
    )
    engine = create_engine(db_url)
    db = SQLDatabase(engine)


   # initialize the graph
    if "graph" not in st.session_state:
        tools = create_tools(st.session_state.db_path)
        st.session_state.graph = create_graph(AGENT_SYSTEM_MESSAGE, tools)

    # used with buttons to help narrow focus
    if "selected_action" not in st.session_state:
        st.session_state["selected_action"] = None



    # Display past messages
    display_chat_messages(st.session_state["messages"])

    # Get the user's input
    user_query = get_user_query()

    # when the users enters a char
    if user_query:
        selected_action = st.session_state.get("selected_action", "Submit") # get the selected action (buttons determine selected action)
        st.session_state.messages.append({"role": "user", "content": user_query, "image": None, "file_data": None, "filename": None}) # add message to history to display
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
            else:
                st.session_state.messages.append({"role": "assistant", "content": response, "image": None, "file_data": None, "filename": None}) # if there is no png, or image just keep image as none
            st.write(response) # write response to screen

        st.session_state["selected_action"] = None # reset selected action

    col1, col2, col3, col4, col5 = st.columns(5) # define conlumns for action buttons

    placeholder = st.empty()
    with placeholder.container(): # put each button in its own column in a container
        with col1: # used to generate code
            if st.button('Code Gen'):
                st.write('Activated!')
                st.session_state["selected_action"] = "Code Gen"

        with col2: # used to generate and execute sql queries
            if st.button('SQL Query'):
                st.write('Activated!')
                st.session_state["selected_action"] = "SQL Query"

        with col3:
            if st.button('Plot Gen'): # used when you want to execute code that generates a plot
                st.write('Activated!')
                st.session_state["selected_action"] = "Plot Gen"
        with col4:
            if st.button('CSV Gen'): # used when you want to execute code that generates a csv file
                st.write(' Activated!')
                st.session_state["selected_action"] = "CSV Gen"
        with col5:
            if st.button('Simple Chat'): # used to just chat with TitanBot 
                st.write(' Activated!')
                st.session_state["selected_action"] = "Simple Chat"

                # you can still generate code and sql queries using simple chat, but it is helpful to TitanBot to define what you are trying to do

    
