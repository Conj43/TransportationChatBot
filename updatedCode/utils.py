# main file is main.py

import pandas as pd

# function to get all column names using sql lite connection c
def get_all_col_names(c):
    c.execute("SELECT name FROM sqlite_master WHERE type='table';") # run query to get all tables
    table_names = c.fetchall()
    table_names = [name[0] for name in table_names]
    
    all_columns = []
    for name in table_names: # for all tables, get all column names
        c.execute(f"PRAGMA table_info({name})")
        columns_info = c.fetchall()
        for col_info in columns_info:
            all_columns.append((name, col_info[1], col_info[2]))  # (table_name, column_name, column_type)
    
    return all_columns # return list of all columns with table name, column name and column type


# function to get all distinct text from columns with text
def collect_text_column_values(conn):
    c = conn.cursor()
    text_column_values = {}

    all_columns = get_all_col_names(c) # calls previous function

    for table_name, column_name, column_type in all_columns:
        if column_type.upper() == 'TEXT': # if current column is a text column
            c.execute(f"SELECT DISTINCT {column_name} FROM {table_name}") # get all distinct text from that column
            unique_values = c.fetchall()
            unique_values = {value[0] for value in unique_values if value[0] is not None}
            text_column_values[f"{table_name}.{column_name}"] = unique_values

    return text_column_values # returns all distinct text values



# function to invoke the agent using query and config
def call_agent(user_query, config, agent):
    return agent.invoke({'input': user_query}, config=config)
