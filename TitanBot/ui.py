# main file is main.py

# imports
import streamlit as st

# imports from other files
from utils import create_graph

# function to display all messages
def display_chat_messages(messages):
    for msg in messages:
        if msg["role"] == "assistant": # check roles to determine avatar
            avatar = "🤖"
        else:
            avatar = "💬"
        st.chat_message(msg["role"], avatar=avatar).write(msg["content"]) # write past message to the ui

# function to return the user input
def get_user_query():
    return st.chat_input(placeholder="Ask me anything!")

# function to clear the message history, also clears the chat history for the bot
def clear_message_history():
    if st.session_state["messages"] is not None:
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]
    if "graph" != None:
        st.session_state.graph = create_graph(st.session_state.db_path)


# sets up streamlit page with title and header
def setup_streamlit_page():
    st.set_page_config(page_title="TitanBot", page_icon="📊")
    st.header('📊 Welcome to TitanBot')
