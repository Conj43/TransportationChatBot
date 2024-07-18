# main file is main.py

# example user input to give to llm
EXAMPLES = [
    {   
        "input": "Can you provide me with the number of accidents that occurred during peak hours?", 
        "query": "SELECT COUNT(*) FROM accidents WHERE strftime('%H', time) BETWEEN '07' AND '09' OR strftime('%H', time) BETWEEN '16' AND '18';"
    },
    {
        "input": "Give me the number of accidents that happened during inclement weather.",
        "query": "SELECT COUNT(*) FROM accidents WHERE WTHR_COND IN ('SNOW', 'FREEZING', 'RAIN') OR RD_SURF_CO IN ('ICE', 'WET', 'SNOW');",
    },
    {
        "input": "Give me the list of counties where accidents occur, sorted by most often to least often.",
        "query": " SELECT COUNTY_NAME,COUNT(COUNTY_NAME) AS count FROM accidents GROUP BY COUNTY_NAME ORDER BY count DESC;",
    },
    {
        "input": "Provide me with the number of accidents that occurred in each season.",
        "query": "SELECT CASE WHEN strftime('%m', time) IN ('06', '07', '08') THEN 'summer' WHEN strftime('%m', time) IN ('12', '01', '02') THEN 'winter' WHEN strftime('%m', time) IN ('03', '04', '05') THEN 'spring' WHEN strftime('%m', time) IN ('09', '10', '11') THEN 'fall' END AS season, COUNT(*) AS number_of_accidents FROM accidents WHERE season IS NOT NULL GROUP BY season;",
    },
    {
        "input": "Return to me the number of rural accidents vs the number of urban accidents that occurred during inclement weather. ",
        "query": "SELECT AREA as area, COUNT(AREA) AS count FROM accidents WHERE (WTHR_COND IN ('SNOW', 'FREEZING', 'RAIN') OR RD_SURF_CO IN ('ICE', 'WET', 'SNOW')) GROUP BY AREA ORDER BY count DESC;",
    },
    {
        "input": "What specific roads have the highest rates of accidents?",
        "query": "SELECT ROUTE, accidents FROM (SELECT ROUTE, COUNT(ROUTE) AS accidents FROM accidents as A GROUP BY ROUTE) AS RouteCounts ORDER BY accidents DESC;",
    },
    {
        "input": "Show me the accidents that occurred in Jackson County during the winter months.",
        "query": "WITH WinterAccidents AS (SELECT * FROM accidents WHERE COUNTY_NAME = 'JACKSON' AND strftime('%m', time) IN ('12', '01', '02')) SELECT LATITUDE, LONGITUDE FROM WinterAccidents;",
    },
    {
        "input": "Tell me how many crashes occurred on a straight portion of road opposed to a curved portion of road. ",
        "query": "SELECT MSHP_ROAD as road, accidents FROM (SELECT MSHP_ROAD, COUNT(MSHP_ROAD) AS accidents FROM accidents AS A GROUP BY MSHP_ROAD) AS RoadCounts ORDER BY accidents DESC;",
    },
    {
        "input": "Provide the population of the city or town where accidents occurred in which the driver ran off the road. ",
        "query": "SELECT POPUL as population FROM accidents WHERE MHTD_ACC_T LIKE '%RAN OFF ROAD%';",
    },
    {
        "input": "Return the injury severity and road surface condition of accidents where a car ran off the road or flipped.",
        "query": "SELECT ACC_SVRTY as injury_severity, RD_SURF_CO as road_surface_condition FROM accidents WHERE MHTD_ACC_T LIKE '%RAN OFF%' OR MHTD_ACC_T LIKE '%OVERTURN%';",
    },
    {
        "input": "Provide me with the top 20 counties with the highest proportion of fatal accidents.",
        "query": "SELECT COUNTY_NAME as county, CAST(SUM(CASE WHEN ACC_SVRTY = 'FATAL' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS fatality_rate FROM accidents GROUP BY COUNTY_NAME ORDER BY fatality_rate DESC LIMIT 20;",
    },
    {
        "input": "How many accidents occurred in St Louis County?",
        "query": "SELECT COUNT(*) AS accident_count FROM accidents WHERE COUNTY_NAME = 'ST. LOUIS'",
    },
    {
        "input": "Map all of the accidents that happened in Boone County.",
        "query": "SELECT LATITUDE as latitude, LONGITUDE as longitude FROM accidents WHERE COUNTY_NAME = 'BOONE';",
    },
    {
        "input": "Map all of the accidents that took place while it was dark out.",
        "query": "SELECT LATITUDE as latitude, LONGITUDE as longitude FROM accidents WHERE LIGHT_COND LIKE '%DARK%';",
    },
    {
        "input": "Could you plot the accidents that involved a fatality.",
        "query": "SELECT LATITUDE as latitude, LONGITUDE as longitude FROM accidents WHERE ACC_SVRTY LIKE '%FATAL%';",
    },
    {
        "input": "Plot the crashes that involved a death during daylight.",
        "query": "SELECT LATITUDE as latitude, LONGITUDE as longitude FROM accidents WHERE LIGHT_COND = 'DAYLIGHT' AND ACC_SVRTY = 'FATAL';",
    },
    {
        "input": "What is the average speed on Highway 99?",
        "query": "SELECT AVG(speed) AS average_speed FROM sample WHERE tmc_code IN (SELECT tmc FROM tmc WHERE road = 'HI-99');"
    },
    {
        "input": "Find the speed index of Highway 99.",
        "query": "SELECT s.tmc_code AS tmc,s.measurement_tstamp, s.speed, s.historical_average_speed, \
            t.start_latitude, t.start_longitude, t.end_latitude, t.end_longitude, t.road, t.direction, t.county, t.miles, \
                 t.road_order, t.f_system FROM sample s JOIN tmc t\
                  ON s.tmc_code = t.tmc WHERE t.road = 'HI-99' AND s.measurement_tstamp >= 'YYYY-MM-DD 07:00:00'\
                AND s.measurement_tstamp < 'YYYY-MM-DD 09:00:00';"
    }

]




# thought process for making congestion map
# first make a dictionary for each 85th percentile for each segment
# then, filter data according to specific request
# create a congestion map of segments along highway 99 during am peak hours



# Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.
# SYSTEM_PREFIX = """Your name is DataBot. You are an agent designed to interact with a SQL database.
# Given an input question, use the sql_db_schema tool, and review the database schema.
# Then, you create a syntactically correct {dialect} query to run, and look at the results of the query and return the answer.

# Never query for all the columns from a specific table, only ask for the relevant columns given the question.

# Only use the given tools. Only use the information returned by the tools to construct your final answer.
# You have access to these tools: [sql_db_query, sql_db_schema, sql_db_list_tables, sql_db_query_checker, search_distinct_text, map_tool, graph_tool].
# DO NOT request to use a tool you do not have access to. 

# If you get an error executing a query, ALWAYS use the sql_sb_list_tables tool, then use sql_db_schema tool, 
# and review the schema before rewriting your query. 
# Use the schema to write your query, do not use the sample data from the schema to generate an answer.
# Always check to make sure you used the correct column name.

# DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

# DO NOT hallucinate, guess or make something up. If the questions is related to the database, you must use a query.
# Only do what the user asks you to do. Don't display data you have not queried.

# If you think a proper noun is mispelled, look up the filter value using the "search_distinct_text" tool. 

# If the question does not seem related to the database, you may use your knwowledge to chat with the user, and remind them to try and query the database.

# If you are asked to map, plot or show something, query for the latitudes and longitudes, then use the map tool.
# Use the coordinate pairs from the query to input into the map tool in order to efficiently call this tool.

# Use the graph_tool to create graphs when requested.
# When inputting into the graph tool, provide an intuitive description of the data being graphed, and input all x and y values.

# Only create one map or graph per query.

# Here are some examples of user inputs and their corresponding SQL queries:"""

SYSTEM_PREFIX="""Your name is DataBot. You are an agent designed to interact with a SQL Database.
Here are your steps of action:
1. Receive an input query from the user
2. Determine if the user's input is related to the database
3. If the question does not seem related to the database, you may use your knwowledge to chat with the user, and remind them to try and query the database.
4. Use the sql_db_schema tool to review the schema of all the tables in the database
5. After you have used sql_db_schema, create a syntactically correct {dialect} query to run. If the query is likely to return a large amount of data or involves complex joins, filtering, or aggregations, use the large_query_tool to run the query.
6. Determine if you need to use one of the tools you have access to
7. Use any tools you need to
8. Return your answer to the user

NOTES:
- DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
- ALWAYS perform your steps of action in order.
- NEVER use large_query_tool until you have used sql_db_schema.
- Use large_query_tool when: 
    - The query is expected to process or return a significant amount of data.
	- The query involves complex calculations, multiple joins, or extensive filtering.
- DO NOT assume example queries will have the same column names as the database you are interacting with
- DO NOT hallucinate, guess or make something up. If the questions is related to the database, you must use a query.
- You have access to these tools: [large_query_tool, sql_db_query, sql_db_schema, sql_db_list_tables, sql_db_query_checker, map_tool, graph_tool].
- If you are asked to map something query for the latitudes and longitudes, then use the map tool.
- If you are asked to graph something, use the query results to input information into the graph tool.
- When you graph data, give a high level interpretation of the graph, as if you were a transportation engineer. Use your knowledge to explain why different trends occur.
- NEVER use the map tool and graph tool at the same time. Only use what is asked of you.


Here are some examples of user inputs and their corresponding SQL queries:"""







# description of our retriever tool
DESCRIPTION_RETRIEVER = """Use to look up values to filter on. Input is an approximate spelling of a piece of text, output is \
    valid spelling of text. Use the text most similar to the search.""" # define a description to help llm think

DESCRIPTION_COLS = """Use this tool to get this correct column names for the database. Input the column names you are looking for, and \
    the tool will retrieve the column names correct to this database."""
