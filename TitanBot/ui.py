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
        if msg.get("file_data") is not None:
            st.download_button(
                label=f"Download {msg["filename"]}",
                data=msg["file_data"],
                file_name=msg["filename"],
                mime='text/csv'
            )
        st.chat_message(msg["role"], avatar=avatar).write(msg["content"]) # write past message to the ui



# function to return the user input
def get_user_query():
    return st.chat_input(placeholder="Ask me anything! Simple Chat is activated by default!")




# function to clear the message history, also clears the chat history for the bot
def clear_message_history():
    st.session_state.db_path = None
    st.sidebar.info("History cleared.")
    if st.session_state["messages"] is not None:
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?", "image": None, "file_data": None, "filename": None}]
    if "graph" in st.session_state:
        tools = create_tools(st.session_state.db_path)
        st.session_state.graph = create_graph(AGENT_SYSTEM_MESSAGE, tools)





# sets up streamlit page with title and header
def setup_streamlit_page():
    st.set_page_config(page_title="TitanBot", page_icon="📊")
    st.header('📊 Welcome to TitanBot')





    




def create_buttons():
    col1, col2, col3, col4, col5 = st.columns(5) # define conlumns for action buttons

    placeholder = st.empty()
    with placeholder.container(): # put each button in its own column in a container
        with col1: # used to generate code
            if st.button('Natural Language to Code'):
                st.write('Activated! You may now enter your chat!')
                st.session_state["selected_action"] = "Code Gen"

        with col2: # used to generate and execute sql queries
            if st.button('Natural Language to SQL Query'):
                st.write('Activated! You may now enter your chat!')
                st.session_state["selected_action"] = "SQL Query"

        with col3:
            if st.button('Execute Code and Display Plot'): # used when you want to execute code that generates a plot
                st.write('Activated! You may now enter your chat!')
                st.session_state["selected_action"] = "Plot Gen"
        with col4:
            if st.button('Execute Code and Download CSV file'): # used when you want to execute code that generates a csv file
                st.write('Activated! You may now enter your chat!')
                st.session_state["selected_action"] = "CSV Gen"
        with col5:
            if st.button('Simple Chat with TitanBot'): # used to just chat with TitanBot 
                st.write('Activated! You may now enter your chat!')
                st.session_state["selected_action"] = "Simple Chat"

                # you can still generate code and sql queries using simple chat, but it is helpful to TitanBot to define what you are trying to do
