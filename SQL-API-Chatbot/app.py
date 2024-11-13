# http://127.0.0.1:5000/api?user_input=Hello

from flask import Flask, request, jsonify

from tools import create_tools
from flask_cors import CORS
from utils import create_agent, call_agent
from heavyai import connect
from db_config import HEAVY_USER, HEAVY_PROTOCOL, HEAVY_DBNAME, HEAVY_HOST, HEAVY_PASSWORD, HEAVY_PORT, URI
import sqlalchemy
from sqlalchemy import create_engine
from langchain_community.utilities.sql_database import SQLDatabase
import pandas as pd
app = Flask(__name__)
CORS(app)

# heavydb://<user>:<pass>@<host>:<port>/<db>?protocol=<protocol>
# uri = "heavydb://" + HEAVY_USER + ":" + HEAVY_PASSWORD + "@" + HEAVY_HOST + ":" + HEAVY_PORT + "/" + HEAVY_DBNAME + "?protocol=" + HEAVY_PROTOCOL
# print(uri)
# engine = create_engine(url=uri)

# # Create the engine
# engine = SQLDatabase.from_uri(uri)

# engine = create_engine(url=URI)


# con = engine.connect()



con = connect(
        user=HEAVY_USER, password=HEAVY_PASSWORD, host=HEAVY_HOST,
        port=HEAVY_PORT, dbname=HEAVY_DBNAME, protocol=HEAVY_PROTOCOL
    )
# print(con)
tools = create_tools(con)
graph = create_agent(tools)
config = {"configurable": {"thread_id": "1"}}


# user_input="whats total number of crashes in 2020 in crashes all out"

# result = call_agent(user_input, config, graph)

# print(result)


@app.route('/api', methods=['GET'])
def chat():
    user_input = request.args.get('user_input', '') 
    result = ''

    if user_input:
        result = call_agent(user_input, config, graph)
    

    print(f"User Input: {user_input}, Response: {result}")


    return jsonify({"user_input": user_input, "response": result})

@app.route('/', methods=['GET'])
def home():
    return jsonify({"user_input": "Hello Chatbot"})

if __name__ == '__main__':
    # app.run( port=80, debug=True)
    app.run(debug=True)


