# imports
import os, io, csv,ast
from dotenv import load_dotenv
from typing import List
from tavily import TavilyClient
from pydantic import BaseModel


# langchain imports
from langchain_openai import ChatOpenAI
from langchain.tools import StructuredTool
from langchain_core.messages import SystemMessage, HumanMessage



def create_tools():

    def add(num1, num2):
        return num1+num2


    # tool that generares the report
    add_tool = StructuredTool.from_function(
        func=add,
        name="add_tool",
        description="Use this tool to add 2 numbers together."
    )

    tools = [add_tool]

    return tools

