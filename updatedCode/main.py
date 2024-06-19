# to run this application: streamlit run main.py

# imports
import os
import tempfile
from dotenv import load_dotenv
import streamlit as st

# langchain imports
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langchain_core.chat_history import BaseChatMessageHistory

# imports from other files
from utils import call_agent
from prompts import full_prompt
from tools import create_map_llm, create_tools
from ui import display_chat_messages, get_user_query, setup_streamlit_page, clear_message_history

# import logging
# logging.getLogger().setLevel(logging.ERROR) # hide warning log

# sets up streamlit page in ui.py
setup_streamlit_page()

# load env variables
load_dotenv()

# define open ai api key
openai_api_key = os.environ['OPENAI_API_KEY']

# create db path state variable
if "db_path" not in st.session_state:
    st.session_state.db_path = None

# create messages state variable
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

# create store variable to keep track of history
if "store" not in st.session_state:
    st.session_state.store = {}




# get an uploaded .db file
if st.sidebar.button("Clear History"):
    clear_message_history()
st.sidebar.subheader("Welcome to our Transportation Database Assistant!")
st.sidebar.markdown("First, upload your database with traffic or accident information, then chat with your data! \
                    You can map your data by asking DataBot to map accidents or crashes with specific queries. \
                    You can also visualze your data by asking DataBot to graph specific data for you!")
st.sidebar.markdown("---")
st.sidebar.subheader("Database Upload")
st.sidebar.markdown("Upload a SQLite .db file for analysis.")
uploaded_file = st.sidebar.file_uploader("Choose a database file", key="bottom_uploader")
# handle when file is uploaded
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





# initializes db to your .db file
if st.session_state.db_path is not None:
    db = SQLDatabase.from_uri(f'sqlite:///{st.session_state.db_path}')

     # method to get chat history for current session id in store
    def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in st.session_state.store:
            st.session_state.store[session_id] = ChatMessageHistory()
        return st.session_state.store[session_id]


    # method to create sql agent with history 
    def create_sql_agent_with_history(db, tools, full_prompt):
        agent = create_sql_agent( # initilaize sql agent
            llm=ChatOpenAI(model="gpt-3.5-turbo", temperature=0),
            db=db,
            prompt=full_prompt,
            verbose=True,
            agent_type="openai-tools",
            extra_tools=tools,
            # return_intermediate_steps=True,
            max_iterations=10,
        )
        

        agent_with_chat_history = RunnableWithMessageHistory( # init runnable with history
            agent,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

        return agent_with_chat_history # return the runnable agent with chat history


    # initialize tools from tools.py function 
    tools = create_tools(st.session_state.db_path)

    # create the agent with chat history
    agent_with_chat_history = create_sql_agent_with_history(db, tools, full_prompt)

    # create map llm which interprets whether or not to use map 
    map_llm = create_map_llm()

    # displays past messages
    display_chat_messages(st.session_state["messages"])

    # gets the users input 
    user_query = get_user_query()

    # if user has submitted input
    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query}) # add the input to messages
        st.chat_message("user", avatar="💬").write(user_query)

        with st.chat_message("assistant", avatar="🤖"):
            st_cb = StreamlitCallbackHandler(st.container()) # use built in langchain function to get call backs to display to container
            config = {"configurable": {"session_id": "123"}, "callbacks": [st_cb]} # initialize config with session id and st_cb is streamlit callbacks
            response = call_agent(user_query, config, agent_with_chat_history) # get the response
            response = response['output'] # just keep the output text from the bot
            st.session_state.messages.append({"role": "assistant", "content": response}) # add output to the end of the messages
            st.write(response) # write it to the screen

            
