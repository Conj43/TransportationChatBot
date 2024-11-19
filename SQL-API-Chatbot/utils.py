# imports 
import os, sqlite3
from dotenv import load_dotenv
from typing import Annotated
from typing_extensions import TypedDict

# langchain imports
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

# initialize SQLite database
conn = sqlite3.connect('chat_history.db', check_same_thread=False)
cursor = conn.cursor()


cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    conversation_id TEXT,
    message TEXT,
    role TEXT,
    state TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# saving messages and state
def save_message(user_id: str, conversation_id: str, message: str, role: str, state: dict):
    # cast as string
    serialized_state = str(state) if state else ""  

    cursor.execute('''
    INSERT INTO messages (user_id, conversation_id, message, role, state)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, conversation_id, message, role, serialized_state))
    conn.commit()

    # only keep 20 most recent messages
    cursor.execute('''
    DELETE FROM messages WHERE id IN (
        SELECT id FROM messages WHERE conversation_id = ?
        ORDER BY timestamp DESC LIMIT 1 OFFSET 19
    )
    ''', (conversation_id,))
    conn.commit()


# retrieve messages from user id and conversation id
def retrieve_messages(user_id: str, conversation_id: str):
    cursor.execute('''
    SELECT role, message, state FROM messages
    WHERE user_id = ? AND conversation_id = ?
    ORDER BY timestamp DESC
    LIMIT 20
    ''', (user_id, conversation_id))
    return [{"role": row[0], "content": row[1], "state": row[2]} for row in cursor.fetchall()]



# call agent defines configuration and invokes graph
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
    memory = MemorySaver()  # initalize memory

    # define state
    class State(TypedDict):
        messages: Annotated[list, add_messages]

    graph_builder = StateGraph(State)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)  
    llm_with_tools = llm.bind_tools(tools)  


    def chatbot(state: State, config):

        user_id = config["configurable"]["user_id"]
        conversation_id = config["configurable"]["thread_id"]

        db_messages = retrieve_messages(user_id, conversation_id)

        all_messages = [system_message] + db_messages + state["messages"]

        response = llm_with_tools.invoke(all_messages)

        if state["messages"]:
            save_message(user_id, conversation_id, state["messages"][-1].content, "user", state)
        if response.content:
            save_message(user_id, conversation_id, response.content, "assistant", state)

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



