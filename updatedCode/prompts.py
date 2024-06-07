# main file is main.py

# langchain imports
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import (
    FewShotPromptTemplate,
    PromptTemplate,
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    MessagesPlaceholder,
)

# imports from other files
from constants import EXAMPLES, SYSTEM_PREFIX


# use semantic search to find k most similar examples to current input
example_selector = SemanticSimilarityExampleSelector.from_examples(
    EXAMPLES,
    OpenAIEmbeddings(),
    FAISS,
    k=5,
    input_keys=["input"],
)

# combines system prefix and exmaples to put them into one
few_shot_prompt = FewShotPromptTemplate(
    example_selector=example_selector,
    example_prompt=PromptTemplate.from_template(
        "User input: {input}\nSQL query: {query}"
    ),
    input_variables=["input", "dialect",  "chat_history"],
    prefix=SYSTEM_PREFIX,
    suffix="",
)

# full prompt adds all our prompt pieces into one big prompt to pass to llm
full_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate(prompt=few_shot_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)
