# main file is main.py
# streamlit run main.py --server.maxUploadSize 400


# imports 
from typing import Annotated
import inspect
from typing import Callable, TypeVar
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from streamlit.delta_generator import DeltaGenerator
from typing_extensions import TypedDict

# langchian imports
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import StreamlitCallbackHandler

# langgraph imports
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# imports form other files




def call_graph(user_input, config, graph):
    response = graph.invoke({"messages": [("user", user_input)]}, config=config)
    # # response["messages"][-1].pretty_print()
    # snapshot = graph.get_state(config)
    # print(snapshot)
    return response["messages"][-1].content


# function to get around streamlit callback handler
T = TypeVar('T')

def get_streamlit_cb(parent_container: DeltaGenerator):
    def decor(fn: Callable[..., T]) -> Callable[..., T]:
        ctx = get_script_run_ctx()
        def wrapper(*args, **kwargs) -> T:
            add_script_run_ctx(ctx=ctx)
            return fn(*args, **kwargs)
        return wrapper

    st_cb = StreamlitCallbackHandler(parent_container=parent_container)

    for name, fn in inspect.getmembers(st_cb, predicate=inspect.ismethod):
        if name.startswith('on_'):
            setattr(st_cb, name, decor(fn))

    return st_cb




# function to create graph
def create_graph(system_message, tools):

    memory = MemorySaver() # initalize memory

    # define class for the state
    class State(TypedDict):
        messages: Annotated[list, add_messages]
    
    
    graph_builder = StateGraph(State)


    llm = ChatOpenAI(model="gpt-4o-mini") # define llm
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
    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )

    # add edge from tools to chatbot
    graph_builder.add_edge("tools", "chatbot")

    # make sure graph always starts at chatbot
    graph_builder.set_entry_point("chatbot")

    # compile graph
    graph = graph_builder.compile(checkpointer=memory)

    return graph # return graph



