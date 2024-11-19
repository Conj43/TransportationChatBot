# imports
import logging
from flask import Flask, request, jsonify
from tools import create_tools
from flask_cors import CORS
from utils import call_agent
from heavyai import connect

# imports from other files
from db_config import HEAVY_USER, HEAVY_PROTOCOL, HEAVY_DBNAME, HEAVY_HOST, HEAVY_PASSWORD, HEAVY_PORT
from prompts import PROMPT




app = Flask(__name__)
CORS(app)

try:
    con = connect(
        user=HEAVY_USER, password=HEAVY_PASSWORD, host=HEAVY_HOST,
        port=HEAVY_PORT, dbname=HEAVY_DBNAME, protocol=HEAVY_PROTOCOL
    )
    tools = create_tools(con)
    logging.info("Database connection established and tools created successfully.")
except Exception as e:
    logging.error(f"Error connecting to database or creating tools/graph: {e}")





@app.route('/api', methods=['GET'])
def chat():
    user_input = request.args.get('user_input', '') 
    user_id = request.args.get('user_id', 'default_user') 
    conversation_id = request.args.get('conversation_id', 'default_conversation') 
    result = ''

    if user_input:
        try:
            result = call_agent(user_input, user_id, conversation_id, PROMPT, tools)
            logging.info(f"Agent called successfully with input: {user_input}")
        except Exception as e:
            logging.error(f"Error during agent call: {e}")
            result = f"Error during agent call: {e}"

    logging.debug(f"User Input: {user_input}, Response: {result}")
    return jsonify({"user_input": user_input, "response": result})

@app.route('/', methods=['GET'])
def home():
    return jsonify({"user_input": "Hello Chatbot"})

if __name__ == '__main__':
    app.run(debug=True)
