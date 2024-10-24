# main file is main.py

# imports
import streamlit as st

# imports from other files
from utils import create_graph, invoke_titanbot
from tools import create_tools
from prompts import AGENT_SYSTEM_MESSAGE


def blank_messages():
    msg = [{"role": "assistant", "content": "How can I help you?", "image": None, "file_data": None, "filename": None, "html": None}]
    return msg

# function to display all messages
def display_chat_messages(messages):
    for msg in messages:
        if msg["role"] == "assistant": # check roles to determine avatar
            avatar = "🤖"
        else:
            avatar = "💬"
        if msg.get("image") is not None:
            st.image(msg["image"], caption='Generated Image', use_column_width=True)

        if msg.get("file_data") is not None: # create button to download file
            st.download_button(
                label=f"Download {msg['filename']}",
                data=msg["file_data"],
                file_name=msg["filename"],
                mime='text/csv'
            )
        if msg.get("html") is not None:

            st.components.v1.html(msg["html"], height=600, scrolling=True) # display map
            st.download_button(
                label=f"Download {msg['filename']}",
                data=msg['html'],
                file_name=msg['filename'],
                mime='text/html'
            )
        st.chat_message(msg["role"], avatar=avatar).write(msg["content"]) # write past message to the ui



# function to return the user input
def get_user_query():
    return st.chat_input(placeholder="Ask me anything! Simple Chat is activated by default!")




# function to clear the message history, also clears the chat history for the bot
def clear_message_history():
    st.session_state.db_path = None
    # st.sidebar.info("History cleared.")
    if st.session_state["messages"] is not None:
        st.session_state["messages"] = blank_messages()
    if "graph" in st.session_state:
        tools = create_tools(st.session_state.db_path)
        st.session_state.graph = create_graph(AGENT_SYSTEM_MESSAGE, tools)
    if "used_filenames" in st.session_state:
        st.session_state.used_filenames = set()





# sets up streamlit page with title and header
def setup_streamlit_page():
    st.set_page_config(page_title="TitanBot", page_icon="📊")
    st.header('📊 Welcome to TitanBot')




def create_buttons():
    col1, col2, col3, col4 = st.columns(4)  # define columns for action buttons
    placeholder = st.empty()
    bool=False
    with placeholder.container():  # put each button in its own column in a container
        with col1:  # used to generate code
            if st.button('Natural Language to Code'):
                st.success('Code Generation Activated! You may now enter your chat!')
                st.session_state["selected_action"] = "Code Gen"


        with col2:  # used to generate and execute SQL queries
            if st.button('Natural Language to SQL Query'):
                st.success('SQL Query Generation Activated! You may now enter your chat!')
                st.session_state["selected_action"] = "SQL Query"


        with col3:
            if st.button('Simple Chat with TitanBot'):  # used to just chat with TitanBot
                st.success('Simple Chat Activated! You may now enter your chat!')
                st.session_state["selected_action"] = "Simple Chat"


        with col4:
            if st.button('Execute Code'):  # used to run the code
                st.success('Code will now be executed!')
                st.session_state["selected_action"] = "Run Code"
                bool=True

    if bool:
        invoke_titanbot("Execute my code please!") # this is just a message the user sees, the real message is different

        


