# main file is main.py

import streamlit as st

# function to display all messages
def display_chat_messages(messages):
    for msg in messages:
        if msg["role"] == "assistant": # check rols to determine avatar
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
    if st.session_state.store is not None:
        st.session_state.store = {}


# sets up streamlit page with title and header
def setup_streamlit_page():
    st.set_page_config(page_title="Database Assistant", page_icon="📊")
    st.header('📊 Welcome to Transportation Database Assistant')
