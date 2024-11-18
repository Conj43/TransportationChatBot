# imports 
import os, sqlite3
from dotenv import load_dotenv
from typing import Annotated
from typing_extensions import TypedDict

# langchian imports
from langchain_openai import ChatOpenAI

# langgraph imports
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# imports from other files
from prompts import PROMPT

# load env variables
load_dotenv()

# define open ai api key
openai_api_key = os.getenv('OPENAI_API_KEY')

# Initialize SQLite database
conn = sqlite3.connect('chat_history.db', check_same_thread=False)
cursor = conn.cursor()

# Create table for storing messages
cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    conversation_id TEXT,
    message TEXT,
    role TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# Database utility functions
def save_message(user_id: str, conversation_id: str, message: str, role: str):
    # Insert the new message
    cursor.execute('''
    INSERT INTO messages (user_id, conversation_id, message, role)
    VALUES (?, ?, ?, ?)
    ''', (user_id, conversation_id, message, role))
    conn.commit()

    # Ensure we only keep the 7 most recent messages for each conversation
    cursor.execute('''
    DELETE FROM messages WHERE id IN (
        SELECT id FROM messages WHERE conversation_id = ?
        ORDER BY timestamp DESC LIMIT 1 OFFSET 9
    )
    ''', (conversation_id,))
    conn.commit()


def retrieve_messages(user_id: str, conversation_id: str):
    cursor.execute('''
    SELECT role, message FROM messages
    WHERE user_id = ? AND conversation_id = ?
    ORDER BY timestamp DESC
    LIMIT 10
    ''', (user_id, conversation_id))
    return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]


# def call_agent(user_input, config, graph):
#     response = graph.invoke({"messages": [("user", user_input)]}, config=config)
#     return response["messages"][-1].content


def call_agent(user_input, user_id, conversation_id, system_message, tools):
    config = {
        "configurable": {
            "user_id": user_id,
            "thread_id": conversation_id
        }
    }
    graph=create_graph(system_message, tools)
    response = graph.invoke({"messages": [("user", user_input)]}, config=config)
    return response["messages"][-1].content



def create_graph(system_message, tools):
    memory = MemorySaver()  # Initialize memory (State Memory)

    # Define class for the state
    class State(TypedDict):
        messages: Annotated[list, add_messages]

    graph_builder = StateGraph(State)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)  # Define LLM
    llm_with_tools = llm.bind_tools(tools)  # Bind tools to LLM



    # def chatbot(state: State):
    #     messages = [system_message] + state["messages"]
    #     # print(f"Messages sent to LLM: {messages}\n\n")  
    #     response = llm_with_tools.invoke(messages)
    #     # print(f"Response from LLM: {response}\n\n")  
    #     return {"messages": [response]}

    def chatbot(state: State, config):
        print("Inside chatbot function")
        user_id = config["configurable"]["user_id"]
        conversation_id = config["configurable"]["thread_id"]

        # Retrieve previous messages from DB
        db_messages = retrieve_messages(user_id, conversation_id)
        print("DB Messages:", db_messages)

        # Combine previous and current messages
        all_messages = [system_message] + db_messages + state["messages"]
        print("All messages:", all_messages)

        # Call the LLM with all messages
        response = llm_with_tools.invoke(all_messages)
        print("LLM Response: ", response)

        # Save user and assistant messages to DB
        if state["messages"]:
            print("i1")
            save_message(user_id, conversation_id, state["messages"][-1].content, "user")
            print("hi")
        if response.content:
            save_message(user_id, conversation_id, response.content, "assistant")

        temp = {"messages": [response]}
        print("temp: ", temp)
        return {"messages": [response]}

    # Add chatbot node
    graph_builder.add_node("chatbot", chatbot)

    # Create tools node
    tool_node = ToolNode(tools=tools)

    # Add tools node
    graph_builder.add_node("tools", tool_node)

    # Add conditional edges
    graph_builder.add_conditional_edges("chatbot", tools_condition)

    # Add edge from tools to chatbot
    graph_builder.add_edge("tools", "chatbot")

    # Make sure graph always starts at chatbot
    graph_builder.set_entry_point("chatbot")

    # Compile graph
    graph = graph_builder.compile(checkpointer=memory)

    return graph  # Return graph



