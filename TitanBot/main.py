# to run this application: streamlit run main.py
# streamlit run main.py --server.maxUploadSize 400

# imports
import os, tempfile
from dotenv import load_dotenv
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL


# langchain imports
from langchain_community.utilities.sql_database import SQLDatabase

# imports from other files
from utils import create_graph, create_db_from_uploaded_csv, fetch_data_and_create_db, invoke_titanbot
from ui import display_chat_messages, get_user_query, setup_streamlit_page, clear_message_history, create_buttons, blank_messages
from prompts import AGENT_SYSTEM_MESSAGE
from tools import create_tools

# load env variables
load_dotenv()

# define open ai api key
openai_api_key = os.environ['OPENAI_API_KEY']

# sets up streamlit page in ui.py
setup_streamlit_page()

# Initialize session state variables
if 'db_path' not in st.session_state:
    st.session_state.db_path = None

if "messages" not in st.session_state:
    st.session_state["messages"] = blank_messages()



# sidebar content
if st.sidebar.button("Clear History"):
    clear_message_history()


# sqlite db upload
st.sidebar.subheader("Database Upload")
st.sidebar.markdown("Upload a SQLite .db file for analysis.")
uploaded_file = st.sidebar.file_uploader("Choose a database file", key="bottom_uploader")




# DB UPLOAD
if uploaded_file is not None:
    if st.session_state.db_path is None:
        if uploaded_file.name.endswith('.db'):
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            temp_file.write(uploaded_file.read())
            temp_file_path = temp_file.name
            temp_file.close()
            st.session_state.db_path = temp_file_path
            st.sidebar.success("Database uploaded successfully.") 
        else:
            st.sidebar.error("Error: The uploaded file is not a .db file. Please try a .db file.")
    else:
        st.sidebar.success("Database uploaded successfully.") 


st.sidebar.markdown("---")

# API UPLOAD
st.sidebar.subheader("Cloud Database Upload")
st.sidebar.markdown("Provide a URL to fetch data:")
data_url = st.sidebar.text_input("Enter URL")

# Handle URL input
if st.sidebar.button("Fetch Data"):
    if data_url:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file_path = temp_file.name
        temp_file.close()
        db_path = fetch_data_and_create_db(data_url, temp_file_path)
        if db_path:
            print(db_path)
            st.session_state.db_path = db_path
            st.sidebar.success("Data fetched and database created successfully.")
    else:
        st.sidebar.error("Error: Please provide a valid URL.")


st.sidebar.markdown("---")
# CSV UPLOAD
st.sidebar.subheader("CSV File Upload")
st.sidebar.markdown("Upload one or more CSV files for analysis.")
uploaded_csv_files = st.sidebar.file_uploader("Choose CSV files", type=['csv'], accept_multiple_files=True, key="csv_uploader")

# Process CSV files
if len(uploaded_csv_files) > 0:
    if st.session_state.db_path is None:
        csv_files = [uploaded_csv_file for uploaded_csv_file in uploaded_csv_files if uploaded_csv_file.type == 'text/csv']
        if csv_files:
            st.session_state.csv_files = csv_files
            db_path = create_db_from_uploaded_csv(csv_files)
            if db_path:
                st.session_state.db_path = db_path
                st.sidebar.success("Database created successfully.")
            else:
                st.sidebar.error("Error: Failed to create the database.")
        else:
            st.sidebar.error("Error: No valid CSV files uploaded.")
    else:
        st.sidebar.success("Database created successfully.")


if uploaded_file is None and len(uploaded_csv_files) == 0 and data_url is None:
    clear_message_history()



# initialize db connection to .db file
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

    if "used_filenames" not in st.session_state:
        st.session_state.used_filenames = set()



    # Display past messages
    display_chat_messages(st.session_state["messages"])

    # get the user's input
    user_query = get_user_query()

    # when the users enters a chat, invoke graph
    if user_query:
        invoke_titanbot(user_query=user_query)


    # create buttons to select modes
    create_buttons()

    

    
