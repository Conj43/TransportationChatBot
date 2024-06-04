##### how to run this:  streamlit run transportation_copilot.py

import os
import tempfile
from dotenv import load_dotenv 
import streamlit as st
from langchain.callbacks.base import BaseCallbackHandler
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_openai import OpenAIEmbeddings
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
import sqlite3
from langchain.agents import Tool
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
import json


# example user input to give to llm
examples = [
    {   
        "input": "Can you give me the number of accidents that occurred during peak hours?", 
        "query": "SELECT COUNT(*) FROM accidents WHERE strftime('%H', time) BETWEEN '07' AND '09' OR strftime('%H', time) BETWEEN '16' AND '18';"
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



st.set_page_config(page_title="Database Assistant", page_icon="📊")
st.header('📊 Welcome to Transportation Database Assistant')

load_dotenv()

#os.environ["HUGGINGFACEHUB_API_TOKEN"]
openai_api_key = os.environ['OPENAI_API_KEY']

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# Display the file uploader at the side
st.sidebar.title("Upload a Database")
uploaded_file = st.sidebar.file_uploader("Choose a database file", key="bottom_uploader")

if "db.path" != st.session_state:
    st.session_state.db_path = None

if uploaded_file is not None:
   temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
   temp_file.write(uploaded_file.read())
   temp_file_path = temp_file.name
   temp_file.close()
   st.session_state.db_path = temp_file_path
   st.sidebar.success("Database uploaded successfully.")

if st.session_state.db_path is not None:
    db = SQLDatabase.from_uri(f'sqlite:///{st.session_state.db_path}')
    conn = sqlite3.connect(st.session_state.db_path)

    example_selector = SemanticSimilarityExampleSelector.from_examples(
        examples,
        OpenAIEmbeddings(),
        FAISS,
        k=5,
        input_keys=["input"],
    )

    if 'store' not in st.session_state:
            st.session_state.store = {}

# db = SQLDatabase.from_uri('sqlite:///new_accident.db')


# Import Azure OpenAI
#from langchain.llms import AzureOpenAI
#from langchain.chat_models import AzureChatOpenAI

# Uncomment these lines if you want to use your AOAI instance.
#llm = AzureOpenAI(deployment_name="text-davinci-003", model_name="text-davinci-003")
#model = AzureChatOpenAI(deployment_name='gpt-35-turbo',openai_api_type="azure")


# initalize llm

# llm = ChatOpenAI(model="gpt-4", temperature=0)


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

    If you need to filter on a proper noun, you must ALWAYS first look up the filter value using the "search_proper_nouns" tool! 

    If the question does not seem related to the database, just return "I don't know" as the answer.

    Here are some examples of user inputs and their corresponding SQL queries:"""





    
    c = conn.cursor()

    # method to get all column names
    def get_all_col_names():
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_names = c.fetchall()
        table_names = [name[0] for name in table_names]
        
        all_columns = []
        for name in table_names:
            c.execute(f"PRAGMA table_info({name})")
            columns_info = c.fetchall()
            for col_info in columns_info:
                all_columns.append((name, col_info[1], col_info[2]))  # (table_name, column_name, column_type)
        
        return all_columns

    # method to get distinct text from text columns
    def collect_text_column_values():
        text_column_values = {}

        # get all names and corresponding data type
        all_columns = get_all_col_names()

        for table_name, column_name, column_type in all_columns:
            # check if it is text
            if column_type.upper() == 'TEXT':
                # get all unique values from the column
                c.execute(f"SELECT DISTINCT {column_name} FROM {table_name}")
                unique_values = c.fetchall()
                unique_values = {value[0] for value in unique_values if value[0] is not None}
                text_column_values[f"{table_name}.{column_name}"] = unique_values

        return text_column_values

    # call function to obtain all text values and define them
    text_values = collect_text_column_values()

    conn.close() # close connection


    vector_db = FAISS.from_texts(text_values, OpenAIEmbeddings()) # embeds our unique text values
    retriever = vector_db.as_retriever(search_kwargs={"k": 5})  # define retriever to our vector db of embedded unique text values
    description = """Use to look up values to filter on. Input is an approximate spelling of the proper noun, output is \
    valid proper nouns. Use the noun most similar to the search.""" # define a description to help llm think




    # formats propmt into correct format, and adds our example inputs and outputs
    few_shot_prompt = FewShotPromptTemplate(
        example_selector=example_selector,
        example_prompt=PromptTemplate.from_template(
            "User input: {input}\nSQL query: {query}"
        ),
        input_variables=["input", "dialect", "top_k", "chat_history"],
        prefix=system_prefix,
        suffix="",
    )

    # combines prompt into one, which we can use to create the agent
    full_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate(prompt=few_shot_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )


    retriever_tool = create_retriever_tool(
        retriever,
        name="search_proper_nouns",
        description=description,
    )

    tools = [
        Tool(
            name="search_proper_nouns",
            func=retriever_tool,
            description=description
        )
    ]



    def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in st.session_state.store:
            st.session_state.store[session_id] = ChatMessageHistory()
        return st.session_state.store[session_id]

    # initilaize agent without retriever tool
    # agent = create_sql_agent(
    #     llm=llm,
    #     db=db,
    #     prompt=full_prompt,
    #     verbose=True,
    #     agent_type="openai-tools",
    # )

    # initalize sql agent with retriever tool
    agent = create_sql_agent(
        llm=llm,
        db=db,
        prompt=full_prompt,
        verbose=True,
        agent_type="openai-tools",
        tools=tools,
    )

    session_id="123"
    message_history = ChatMessageHistory()

    agent_with_chat_history = RunnableWithMessageHistory(
        agent,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    
    
    if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

    for msg in st.session_state.messages:
        if msg["role"] == "assistant":
            avatar = "🤖"
        else:
            avatar = "💬"
        st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

    user_query = st.chat_input(placeholder="Ask me anything!")

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        st.chat_message("user",avatar="💬").write(user_query)

        with st.chat_message("assistant", avatar="🤖"):
            st_cb = StreamlitCallbackHandler(st.container())
            config = {"configurable": {"session_id": session_id}, "callbacks": [st_cb]}
            response = agent_with_chat_history.invoke({'input': user_query}, config=config)
            response = response.get("output", "")
            response = json.dumps(response, indent=4)
            response = response.strip('"')
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.write(response)



# response = agent.run(user_query, callbacks = [st_cb])
