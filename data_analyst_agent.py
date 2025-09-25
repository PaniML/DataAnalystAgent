from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import Tool, tool
from typing import TypedDict, List
from typing_extensions import Annotated
import subprocess
from dotenv import load_dotenv
import os


load_dotenv()

@tool
def analyst_coder_tool(file_path: str, code: str):
    '''This tool analyzes excel or csv files and performs write operation in a python file `temp.py` and runs it.
    

    Parameters:
    file_path: path of the file the file path is strictly excel or a csv
    code: Python code for analysis
    '''

    if file_path.endswith("csv") or file_path.endswith("xlsx"):
        with open("temp.py", "w") as f:
            f.write(code)

        res = subprocess.run(['python', 'temp.py'], capture_output=True)
    
        return f"After running `temp.py` the output is {res.stdout}"
        #return f"code written to `temp.py` now run temp.py\n\n  code content: {code}"
    else:
        return f"{file_path} is not an excel or a csv. Please select the required file"


@tool
def python_libraries_installer(commands: List[str]):
    '''This tool will be used to install required python libraries from the code.
    Run the pip install commands
    If the python code `temp.py` in current directory is executed correctly you do not need to invoke the tool again
    Otherwise retry installing modules
    parameters:
    commands: full List of pip install commands ex ['pip install requests']
    '''

    message = ""
    for command in commands:
        command = command.split()
        x = subprocess.run(command, capture_output=True)
        if x.returncode == 0:
            message += f"Command {' '.join(command)} executed successfully\nLogs: {x.stdout}\n\n"
        else:
            message += f"Command {' '.join(command)} Failed\nLogs: {x.stderr} try another command\n\n"
    return message


@tool
def code_executor():
    '''Executes `temp.py 
    Once we write to temp.py we run the file `temp.py`
    '''
    res = subprocess.run(['python', 'temp.py'], capture_output=True)
    
    return f"After running `temp.py` the output is {res.stdout}"




SYSTEM_PROMPT = '''YOU are a DATA ANALYST.
Your job is to do analysis on excel or csv files modify and run python code `temp.py` and answer the user query
Use pandas for analysis

### For excel you just read the default sheet 

You may also have to give plots as requested by user:
1. If there are any plots involved please save them as a png file
2. Ensure plots are saved in current directory 
3. Plotting done by matplotlib

INSTRUCTIONS:
STEPS To follow to analyze data:
1. Install necessary libraries by running pip install
2. Then Write the python code to `temp.py` that caters the user query
    a. You may not get the answer directly just by running the code you generate this is iterative process as you need to understand the data
    b. Do not blindly generate the code try to analyze columns have some print statements
    c. Have some print statements so that u arrive to the solution
    d. printing out some pandas processing statement intermediately will guide you to answer the user query
    e. This is how you fix errors gradually
3. Then Execute the code `temp.py`
4. You have to Repeat the process till you get the answer

Note: If the file is not a csv or xlsx please end by responding only csv and excels supported you do not need to perfor codig in that case
'''









class State(TypedDict):
    messages: Annotated[List, add_messages]


llm = ChatGoogleGenerativeAI(model='gemini-2.5-pro', google_api_key=os.environ['GEMINI_KEY'], temperature=0.0).bind_tools(
    [analyst_coder_tool, python_libraries_installer]
)

def agent(state: State):
    print(SYSTEM_PROMPT)
    prompt = f'''SYSTEM PROMPT: {SYSTEM_PROMPT}
    Messages: {state['messages']}
'''
    
    print("**********************")
    print(state['messages'])
    print("*******************************")
    return {"messages": [llm.invoke(prompt)]}
    


def tools_condition(state: State):
    print(state['messages'][-1].tool_calls)
    if state['messages'][-1].tool_calls:
        return 'tools'
    else:
        return END


tools = ToolNode([
                          analyst_coder_tool, python_libraries_installer
                      ])

#################################### WorkFlow ###################################################

workflow = StateGraph(State)
workflow.add_node("agent",agent)
workflow.add_node("tools", tools)

workflow.add_edge(START, "agent")
workflow.add_edge("tools", "agent")
workflow.add_conditional_edges("agent", tools_condition)


graph = workflow.compile()


query = input("Enter the user query:\n")

messages = {"messages": [{
    "role": "user",
    "content": query
}]}


res = graph.invoke(messages)


print("END\n")
print(res['messages'][-1].content)



