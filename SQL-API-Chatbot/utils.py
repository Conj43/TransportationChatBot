# imports 
import os
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


def call_agent(user_input, config, graph):
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



    def chatbot(state: State):
        messages = [system_message] + state["messages"]
        # print(f"Messages sent to LLM: {messages}\n\n")  
        response = llm_with_tools.invoke(messages)
        # print(f"Response from LLM: {response}\n\n")  
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



