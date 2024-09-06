# to run this application: streamlit run main.py
# streamlit run main.py --server.maxUploadSize 400

# imports
import os
import tempfile
from dotenv import load_dotenv
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
import requests
import sqlite3

# langchain imports
from langchain_community.utilities.sql_database import SQLDatabase

# imports from other files
from utils import call_graph, get_streamlit_cb, create_graph
from ui import display_chat_messages, get_user_query, setup_streamlit_page, clear_message_history
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
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]


# Sidebar content
if st.sidebar.button("Clear History"):
    clear_message_history()
st.sidebar.subheader("Welcome to our Transportation Database Assistant!")
st.sidebar.markdown("First, upload your database with traffic or accident information, then chat with your data! \
                    You can map your data by asking TitanBot to map accidents or crashes with specific queries. \
                    You can also visualize your data by asking TitanBot to graph queried data for you!")
st.sidebar.markdown("---")
st.sidebar.subheader("Database Upload")
st.sidebar.markdown("Upload a SQLite .db file for analysis.")
uploaded_file = st.sidebar.file_uploader("Choose a database file", key="bottom_uploader")

# Handle file upload
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
        query={"mode": "ro"}
    )
    engine = create_engine(db_url)
    db = SQLDatabase(engine)


   # initialize the graph
    if "graph" not in st.session_state:
        tools = create_tools(st.session_state.db_path)
        st.session_state.graph = create_graph(AGENT_SYSTEM_MESSAGE, tools)



    # displays past messages
    display_chat_messages(st.session_state["messages"])

    # gets the users input 
    user_query = get_user_query()

    # if user has submitted input
    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query}) # add the input to messages
        st.chat_message("user", avatar="💬").write(user_query)

        with st.chat_message("assistant", avatar="🤖"):
            st_cb = get_streamlit_cb(st.container())
            config = {"configurable": {"thread_id": "1"}, "callbacks": [st_cb]}
            response = call_graph(user_query, config, st.session_state.graph) # get the response
            st.session_state.messages.append({"role": "assistant", "content": response}) # add output to the end of the messages
            st.write(response) # write it to the screen

            
