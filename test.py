from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_openai import OpenAIEmbeddings
from langchain.agents.agent_toolkits import create_retriever_tool
import sqlite3

from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
# example user input to give to llm
examples = [
    {   
        "input": "Can you give me the number of accidents that occurred during peak hours?", 
        "query": "SELECT COUNT(*) FROM accidents WHERE strftime('%H', datetime_) BETWEEN '07' AND '09' OR strftime('%H', datetime_) BETWEEN '16' AND '18';"
    },
    {
        "input": "Show the number of accidents that happened during inclement weather.",
        "query": "SELECT COUNT(*) FROM accidents WHERE WTHR_COND_ IN ('SNOW', 'FREEZING', 'RAIN') OR RD_SURF_CO IN ('ICE', 'WET', 'SNOW');",
    },
    {
        "input": "Give me the list of counties where accidents occur, sorted by most often to least often.",
        "query": " SELECT COUNTY_NAM,COUNT(COUNTY_NAM) AS count FROM accidents GROUP BY COUNTY_NAM ORDER BY count DESC;",
    },
    {
        "input": "Provide me with the number of accidents that occurred in each season.",
        "query": "SELECT CASE WHEN strftime('%m', datetime_) IN ('06', '07', '08') THEN 'summer' WHEN strftime('%m', datetime_) IN ('12', '01', '02') THEN 'winter' WHEN strftime('%m', datetime_) IN ('03', '04', '05') THEN 'spring' WHEN strftime('%m', datetime_) IN ('09', '10', '11') THEN 'fall' END AS season, COUNT(*) AS number_of_accidents FROM accidents WHERE season IS NOT NULL GROUP BY season;",
    },
    {
        "input": "Return to me the number of rural accidents vs the number of urban accidents that occurred during inclement weather. ",
        "query": "SELECT MSHP_AREA_ as area, COUNT(MSHP_AREA_) AS count FROM accidents WHERE (WTHR_COND_ IN ('SNOW', 'FREEZING', 'RAIN') OR RD_SURF_CO IN ('ICE', 'WET', 'SNOW')) GROUP BY MSHP_AREA_ ORDER BY count DESC;",
    },
    {
        "input": "What specific roads have the highest rates of accidents?",
        "query": "SELECT ROUTE, accidents FROM (SELECT ROUTE, COUNT(ROUTE) AS accidents FROM accidents as A GROUP BY ROUTE) AS RouteCounts ORDER BY accidents DESC;",
    },
    {
        "input": "Show me the number of accidents that occurred in Boone County during the winter months.",
        "query": "WITH WinterAccidents AS (SELECT * FROM accidents WHERE COUNTY_NAM = 'BOONE' AND strftime('%m', datetime_) IN ('12', '01', '02')) SELECT COUNT(*) AS accident_count FROM WinterAccidents;",
    },
    {
        "input": "Tell me how many crashes occurred on a straight portion of road opposed to a curved portion of road. ",
        "query": "SELECT MSHP_ROAD as road, accidents FROM (SELECT MSHP_ROAD, COUNT(MSHP_ROAD) AS accidents FROM accidents AS A GROUP BY MSHP_ROAD) AS RoadCounts ORDER BY accidents DESC;",
    },
    {
        "input": "Provide the population of the city or town where accidents occurred in which the driver ran off the road. ",
        "query": "SELECT MSHP_POPUL as population FROM accidents  WHERE MHTD_ACC_T LIKE '%RAN OFF ROAD%';",
    },
    {
        "input": "Return the injury severity and road surface condition of accidents where a car ran off the road or flipped.",
        "query": "SELECT ACC_SVRTY_ as injury_severity, RD_SURF_CO as road_surface_condition FROM accidents WHERE MHTD_ACC_T LIKE '%RAN OFF%' OR MHTD_ACC_T LIKE '%OVERTURN%';",
    },
    {
        "input": "Show the top 20 counties with the highest proportion of fatal accidents.",
        "query": "SELECT COUNTY_NAM as county, CAST(SUM(CASE WHEN ACC_SVRTY_ = 'FATAL' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS fatality_rate FROM accidents GROUP BY COUNTY_NAM ORDER BY fatality_rate DESC LIMIT 20;",
    },
]


# connection to db
db = SQLDatabase.from_uri("sqlite:///new_accident.db")

# initalize llm
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# selects input examples to include in the prompt, based on a semantic search of their embeddings and vector store to find the most similar
example_selector = SemanticSimilarityExampleSelector.from_examples(
    examples,
    OpenAIEmbeddings(),
    FAISS,
    k=5,
    input_keys=["input"],
)


# prefix to define how we want the model to think
system_prefix = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the given tools. Only use the information returned by the tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

If the question does not seem related to the database, just return "I don't know" as the answer.

Here are some examples of user inputs and their corresponding SQL queries:"""


# formats propmt into correct format, and adds our example inputs and outputs
few_shot_prompt = FewShotPromptTemplate(
    example_selector=example_selector,
    example_prompt=PromptTemplate.from_template(
        "User input: {input}\nSQL query: {query}"
    ),
    input_variables=["input", "dialect", "top_k"],
    prefix=system_prefix,
    suffix="",
)

# combines prompt into one, which we can use to create the agent
full_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate(prompt=few_shot_prompt),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

# example prompt, uncomment line below the prompt to view an example of the prompt
prompt_val = full_prompt.invoke(
    {
        "input": "How many accidents happened in Boone County?",
        "top_k": 5,
        "dialect": "SQLite",
        "agent_scratchpad": [],
    }
)
# print(prompt_val.to_string())

# conn = sqlite3.connect("new_accident.db")
# c = conn.cursor()


# def get_all_col_names():
#     c.execute("SELECT name FROM sqlite_master WHERE type='table';")
#     table_names = c.fetchall()
#     table_names = [name[0] for name in table_names]
    
#     all_columns = []
#     for name in table_names:
#         c.execute(f"PRAGMA table_info({name})")
#         columns_info = c.fetchall()
#         for col_info in columns_info:
#             all_columns.append((name, col_info[1], col_info[2]))  # (table_name, column_name, column_type)
    
#     return all_columns

# def collect_text_column_values():
#     text_column_values = {}

#     # Get all column names and their data types
#     all_columns = get_all_col_names()

#     for table_name, column_name, column_type in all_columns:
#         # Check if the column type is TEXT
#         if column_type.upper() == 'TEXT':
#             # Fetch all unique values from this text column
#             c.execute(f"SELECT DISTINCT {column_name} FROM {table_name}")
#             unique_values = c.fetchall()
#             unique_values = {value[0] for value in unique_values if value[0] is not None}
#             text_column_values[f"{table_name}.{column_name}"] = unique_values

#     return text_column_values

# # call function to obtain all text values and define them
# text_values = collect_text_column_values()

# conn.close() # close connection

# vector_db = FAISS.from_texts(text_values, OpenAIEmbeddings())
# retriever = vector_db.as_retriever(search_kwargs={"k": 5})
# description = """Use to look up values to filter on. Input is an approximate spelling of the proper noun, output is \
# valid proper nouns. Use the noun most similar to the search."""
# retriever_tool = create_retriever_tool(
#     retriever,
#     name="search_proper_nouns",
#     description=description,
# )

# initalize sql agent without retriever tool
agent = create_sql_agent(
    llm=llm,
    db=db,
    prompt=full_prompt,
    verbose=True,
    agent_type="openai-tools",
)


# initalize sql agent with retriever tool
# agent = create_sql_agent(
#     llm=llm,
#     db=db,
#     extra_tools=[retriever_tool],
#     prompt=full_prompt,
#     verbose=True,
#     agent_type="openai-tools",
# )



# provide input and get back output from model
agent.invoke({"input": "How many crashes happened where inclement weather played a factor?"})










        
# prompt_prefix = """
# ## Instructions:
# Please act as an expert in SQL. 
# Given user input in human language, follow these steps to create a syntactically correct {dialect} query to retrieve the answer from the database.

# ### Steps to Follow:
# 1. **Review the Database Schema**: Carefully examine the provided schema to understand the available tables and columns.
# 2. **Formulate the Query**: Create a query that:
#     - Retrieves only the relevant columns based on the question.
#     - Limits results to at most {top_k} entries, ordered by a relevant column.
#     - Strictly adheres to the provided table and column names.
# 3. **Case Sensitivity**: Use database schema to look at capitalization for entries, columns and tables, and use the same rules when querying.
# 4. **Check Your Work**: Double-check the query for correctness and handle any potential errors appropriately.


# ### Key Points:
# - **No DML Statements**: Do not perform INSERT, UPDATE, DELETE, DROP, or any other DML statements.
# - **No Guesswork**: Do not guess or use any column names or tables not explicitly provided in the schema.
# - **No Data Generation**: Do not generate any data. If the SQL query returns no results, verify the query and try again.
# - **Return Only Answers**: Never return your query. Use the query results to form your answer to the user's question. Only return your final answer.


# ### Query Execution Guidelines:
# - **Schema Adherence**: Use only the provided table and column names.
# - **No Unspecified Filters**: If the question does not specify a time filter, do not include it in the query.


# ## Tools:


# """

# prompt_format_instructions = """
# Use the following format:

# Question: the input question you must answer
# Thought: think about what to do and use your instructions to define specified terms
# Action: the action to take, should be one of [{tool_names}]
# Action Input: the input to the action
# Observation: the result of the action. 
# ...(repeat Thought/Action/Action Input/Observation as needed)
# Thought: I now know the final answer
# Final Answer: the final answer to the original input question.


# ## Example of Format:

# #### Question:
# Show the number of accidents that happened during inclement weather.

# #### Thought:
# I need to find the number of accidents that occurred during inclement weather.

# #### Action:
# Review SQL Schema

# #### Observation:
# There is a WTHR_COND_ column, this must correspond to the weather at the time of the accident.

# #### Thought:
# I will write a query to find the number of inclement weather entries under WTHR_COND_

# #### Action:
# SQL Query

# #### Action Input:
# ```sql
# SELECT COUNT(*)
# FROM accidents
# WHERE WTHR_COND_ = 'INCLEMENT';
# ```sql

# #### Observation:
# There are no entries where the weather condition was inclement.

# ####Thought: 
# I will review the schema again, and use my knowledge to determie if any of the weather conditions entered are inclement.

# #### Action:
# Review SQL Schema

# #### Observation:
# There are entries such as RAIN, FREEZING and SNOW under WTHR_COND, and those correspond to inclement weather conditions.

# #### Thought:
# I can write a query to find accidents that took place in rain, freezing or snow weather conditions.

# #### Action:
# SQL Query

# #### Action Input:
# ```sql
# SELECT COUNT(*)
# FROM accidents
# WHERE WTHR_COND_ IN ('SNOW', 'FREEZING', 'RAIN');
# ```sql
# #### Observation:
# I used the SQL query to filter accidents where weather conditions were categorized as 'SNOW', 'FREEZING', 'RAIN'.

# #### Final Answer:
# The number of accidents that happened during inclement weather is...



# """




# # Explanation:

# # <===Beginning of an Example of Explanation:
# # Question: Show the number of accidents that happened during inclement weather.
# # Thought: I need to find the number of accidents that occurred during inclement weather. If there is no specific entry for inclement weather, I will look for accidents where weather conditions were unfavorable, such as snowy, icy, or rainy conditions. I associate weather and road conditions together.
# # Action: SQL Query
# # Action Input:

# # ```sql
# # SELECT COUNT(*)
# # FROM accidents
# # WHERE WTHR_COND_ IN ('SNOW', 'FREEZING', 'RAIN')
# #    OR RD_SURF_CO IN ('ICE', 'WET', 'SNOW');
# # ''''sql
# # Observation: I used the SQL query to filter accidents where weather conditions were categorized as 'SNOW', 'FREEZING', 'RAIN' or road surface conditions were 'ICE', 'WET', 'SNOW'.
# # Final Answer: The number of accidents that happened during inclement weather is...
# # ===>End of an Example of Explanation

# # total_prompt = prompt_prefix + prompt_format_instructions

