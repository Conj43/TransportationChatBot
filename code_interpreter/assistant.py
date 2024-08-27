from openai import OpenAI

client = OpenAI()


# Upload a file with an "assistants" purpose
file1 = client.files.create(
  file=open("sample.csv", "rb"),
  purpose='assistants'
)

file2 = client.files.create(
  file=open("tmc.csv", "rb"),
  purpose='assistants'
)



# Create an assistant using the file ID
assistant = client.beta.assistants.create(
  instructions="You are a personal math tutor. When asked a math question, write and run code to answer the question.",
  model="gpt-4o-mini",
  tools=[{"type": "code_interpreter"}],
  tool_resources={
    "code_interpreter": {
      "file_ids": [file1.id, file2.id]
    }
  }
)



import openai
import time
openai.api_key = "YOUR OPENAI API KEY"

assistant_id = "YOUR ASSISTANT ID"


def create_thread(ass_id,prompt):
    #Get Assitant
    #assistant = openai.beta.assistants.retrieve(ass_id)

    #create a thread
    thread = openai.beta.threads.create()
    my_thread_id = thread.id


    #create a message
    message = openai.beta.threads.messages.create(
        thread_id=my_thread_id,
        role="user",
        content=prompt
    )

    #run
    run = openai.beta.threads.runs.create(
        thread_id=my_thread_id,
        assistant_id=ass_id,
    ) 

    return run.id, thread.id


def check_status(run_id,thread_id):
    run = openai.beta.threads.runs.retrieve(
        thread_id=thread_id,
        run_id=run_id,
    )
    return run.status

my_run_id, my_thread_id = create_thread(assistant_id,"find the speed index for all tmc for the entire year. Calculate this by dividing historical average speed over 85th percentile of speed, and only use data during peak hours. peak hours is defined as 6am-8am and 3pm-5pm. display your results including speed and historical average speed")

status = check_status(my_run_id,my_thread_id)

while (status != "completed"):
    status = check_status(my_run_id,my_thread_id)
    time.sleep(2)

response = openai.beta.threads.messages.list(
  thread_id=my_thread_id
)

if response.data:
    print(response.data[0].content[0].text.value)