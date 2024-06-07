# main file is main.py

# example user input to give to llm
EXAMPLES = [
    {   
        "input": "Can you provide me with the number of accidents that occurred during peak hours?", 
        "query": "SELECT COUNT(*) FROM accidents WHERE strftime('%H', time) BETWEEN '07' AND '09' OR strftime('%H', time) BETWEEN '16' AND '18';"
    },
    {
        "input": "Give me the number of accidents that happened during inclement weather.",
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
        "input": "Show me the accidents that occurred in Jackson County during the winter months.",
        "query": "WITH WinterAccidents AS (SELECT * FROM accidents WHERE COUNTY_NAM = 'JACKSON' AND strftime('%m', datetime_) IN ('12', '01', '02')) SELECT LANDED_LAT, LANDED_LON FROM WinterAccidents;",
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
    {
        "input": "How many accidents occurred in St Louis County?",
        "query": "SELECT COUNT(*) AS accident_count FROM accidents WHERE COUNTY_NAM = 'ST. LOUIS'",
    },
    {
        "input": "Map all of the accidents that happened in Boone County.",
        "query": "SELECT LANDED_LAT as latitude, LANDED_LON as longitude FROM accidents WHERE COUNTY_NAM = 'BOONE';",
    },
    {
        "input": "Map all of the accidents that took place while it was dark out.",
        "query": "SELECT LANDED_LAT as latitude, LANDED_LON as longitude FROM accidents WHERE LIGHT_COND LIKE '%DARK%';",
    },
    {
        "input": "Could you plot the accidents that involved a fatality.",
        "query": "SELECT LANDED_LAT as latitude, LANDED_LON as longitude FROM accidents WHERE ACC_SVRTY_ LIKE '%FATAL%';",
    },
]




# Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most {top_k} results.
SYSTEM_PREFIX = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.

You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the given tools. Only use the information returned by the tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

DO NOT guess or make something up.

If you think a proper noun is mispelled, you must ALWAYS first look up the filter value using the "search_distinct_text" tool! 

If the question does not seem related to the database, return "I'm not sure." as the answer.

If you are asked to map something, return only the latitudes and longitudes in the format '(latitude, longitude), (latitude, longitude), ...'.

Here are some examples of user inputs and their corresponding SQL queries:"""


# description of our retriever tool
DESCRIPTION = """Use to look up values to filter on. Input is an approximate spelling of a piece of text, output is \
    valid spelling of text. Use the text most similar to the search.""" # define a description to help llm think