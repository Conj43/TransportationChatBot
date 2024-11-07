# imports



# langchain imports

from langchain.tools import StructuredTool




def create_tools():

    def add(num1, num2):
        return num1+num2


    # tool that generares the report
    add_tool = StructuredTool.from_function(
        func=add,
        name="add_tool",
        description="Use this tool to add 2 numbers together."
    )

    tools = [add_tool]

    return tools

