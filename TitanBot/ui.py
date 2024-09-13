# main file is main.py

# imports
import streamlit as st

# imports from other files
from utils import create_graph
from tools import create_tools
from prompts import AGENT_SYSTEM_MESSAGE

# function to display all messages
def display_chat_messages(messages):
    for msg in messages:
        if msg["role"] == "assistant": # check roles to determine avatar
            avatar = "🤖"
        else:
            avatar = "💬"
        if msg.get("image") is not None:
            st.image(msg["image"], caption='Generated Image', use_column_width=True)
        st.chat_message(msg["role"], avatar=avatar).write(msg["content"]) # write past message to the ui


# function to return the user input
def get_user_query():
    return st.chat_input(placeholder="Ask me anything! Simple Chat is activated by default!")

# function to clear the message history, also clears the chat history for the bot
def clear_message_history():
    if st.session_state["messages"] is not None:
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?", "image": None}]
    if "graph" != None:
        tools = create_tools(st.session_state.db_path)
        st.session_state.graph = create_graph(AGENT_SYSTEM_MESSAGE, tools)


# sets up streamlit page with title and header
def setup_streamlit_page():
    st.set_page_config(page_title="TitanBot", page_icon="📊")
    st.header('📊 Welcome to TitanBot')

# modify user query based on current selected action
def get_selected_action(user_query, selected_action):
    if selected_action == "Code Gen":
        return "First look at the schema for all tables in this database. Then write a python code to accomplish the following: " + user_query + " This math \
            should be calculated in the python code, do not try to make calculations in your sql query. Then show me the code you generate."
    
    elif selected_action == "SQL Query":
        return "First look at the schema for all tables in this database. Then write a sql query to answer this query: " + user_query  + " Then run this query \
            and tell me the results."
    
    elif selected_action == "Plot Gen":
        return "Use the most recent code and input it into graph_tool. Make sure to print the information that will be used to make the graph. \
            Here is the user's query: " + user_query + " If their query does not relate, or the code is not meant to be graphed, ask them for clarification. \
                You may generate some code if there has been no code generated in your conversation yet."
    
    elif selected_action == "CSV Gen":
        return "Use the most recent code and input it into csv_tool. Here is the user's query: " + user_query + " If their query does not relate, \
            or the code is not able to save a csv, ask for clarification. You may generate some code if there has been no code generated in your conversation yet."
    
    elif selected_action == "Simple Chat":
        return user_query
    
    else:
        return user_query # no modifiaction
