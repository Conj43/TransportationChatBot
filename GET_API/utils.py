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


# load env variables
load_dotenv()

# define open ai api key
openai_api_key = os.getenv('OPENAI_API_KEY')


def call_graph(user_input, config, graph):
    response = graph.invoke({"messages": [("user", user_input)]}, config=config)
    # # response["messages"][-1].pretty_print()
    # snapshot = graph.get_state(config)
    # print(snapshot)
    return response["messages"][-1].content


# function to create graph, pass in system message and tools for graph
def create_graph(system_message, tools):

    memory = MemorySaver() # initalize memory

    # define class for the state
    class State(TypedDict):
        messages: Annotated[list, add_messages]
    
    graph_builder = StateGraph(State)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) # define llm
    tools = tools # set tools equal to tools
    llm_with_tools = llm.bind_tools(tools) # bind tools to llm
    
    system_message = system_message

    def chatbot(state: State):
        messages = [system_message] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # add chatbot node
    graph_builder.add_node("chatbot", chatbot)

    # create tools node
    tool_node = ToolNode(tools=tools)

    # add tools node
    graph_builder.add_node("tools", tool_node)

    # add conditional edges
    graph_builder.add_conditional_edges("chatbot",tools_condition,)

    # add edge from tools to chatbot
    graph_builder.add_edge("tools", "chatbot")

    # make sure graph always starts at chatbot
    graph_builder.set_entry_point("chatbot")

    # compile graph
    graph = graph_builder.compile(checkpointer=memory)

    return graph # return graph