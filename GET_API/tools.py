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


# load env variables
load_dotenv()

# define open ai api key
TAVILY_api_key = os.getenv('TAVILY_API_KEY')

def create_tools():
    # function to generate report
    def report_gen(info):
        llm = ChatOpenAI(model="gpt-4o-mini")
        # prompt to help llm generate queries for us
        QUERY_PROMPT = """You are a MoDOT employee that is focused on data in Missouri.
                    Your job is to generate an informative and reliable report. 
                    You will be given the user query, and you must generate a list of search queries that will gather 
                    any relevant information. Only generate 3 queries max."""

        # use llm to generate queries t get a more focused search
        queries = llm.with_structured_output(Queries).invoke([
            SystemMessage(content=QUERY_PROMPT),
            HumanMessage(info)
        ])

        # use tavily to find outside info on internet
        tavily = TavilyClient()
        all_responses = []

        # invoke tavily using each of the queries we generated (max of 3)
        for query in queries.queries:
            # print("query: ", query)
            response = tavily.search(query=query, max_results=1)
            
            # apped results to a list that keeps track of all results
            for r in response['results']:
                all_responses.append(r)
                # all_responses.append(r['content'])
                # print(r['content'])
                # print(r)


        # use llm to then summarize our list of all results
        temp = """You are a MoDOT employee that is focused on data in Missouri.
            You just searched for data and here are the search results:\n
            {compiled_info}\n
            Please compile this information into a formal concise summary.
            Here is the user's input for context:\n
            {info}\n
            Use the URLs given to cite your sources."""

        prompt = temp.format(compiled_info=all_responses, info=info)

        response = llm.invoke(prompt)
        
        # return the summarized info as a report which the agent will use to make a report about the given info
        return response.content


    # tool that generares the report
    report_tool = StructuredTool.from_function(
        func=report_gen,
        name="report_tool",
        description="Use this tool to generate a report. Input the user query into this tool. \
            This tool will retrieve multiple responses and summarize them for you. \
                Do not make any changes to the report, display them directly to the user."
    )

    tools = [report_tool]

    return tools

class Queries(BaseModel):
    queries: List[str]