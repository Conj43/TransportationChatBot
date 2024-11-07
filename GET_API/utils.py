# imports 
import os
from dotenv import load_dotenv


# langchian imports
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate


# langgraph imports
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from prompts import PROMPT

# load env variables
load_dotenv()

# define open ai api key
openai_api_key = os.getenv('OPENAI_API_KEY')


def call_agent(user_input, config, graph):
    prompt_template = PromptTemplate(input_variables=["question"], template=PROMPT)
    formatted_query = prompt_template.format(question=user_input)
    response = graph.invoke({"messages": [("user", formatted_query)]}, config=config)
    return response["messages"][-1].content



def create_agent(tools):

    memory = MemorySaver()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


    agent_executor = create_react_agent(llm, tools, checkpointer=memory)

    return agent_executor
