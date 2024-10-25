from flask import Flask, request, jsonify
from tools import create_tools
from prompts import AGENT_SYSTEM_MESSAGE
from utils import create_graph, call_graph

app = Flask(__name__)


tools = create_tools()
graph = create_graph(AGENT_SYSTEM_MESSAGE, tools)
config = {"configurable": {"thread_id": "1"}}

@app.route('/api', methods=['GET'])
def chat():
    user_input = request.args.get('user_input', '') 
    result = ''

    if user_input:
        result = call_graph(user_input, config, graph)

    return jsonify({"user_input": user_input, "response": result})

if __name__ == '__main__':
    app.run(debug=True)

