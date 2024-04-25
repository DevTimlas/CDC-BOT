from flask import Flask, request, jsonify, render_template, session
import re, uuid
import phonenumbers
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

user_states = {}

# collected_details = []
rand_key = str(uuid.uuid4())
# memory = ConversationBufferMemory(memory_key=rand_key, return_messages=True)

def ask_ai(memory):
    llm = ChatOpenAI(temperature=0, openai_api_key="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", model='gpt-4')
    sys_prompt = open('ask_user_details_new.txt', 'r').read().strip()
    prompt = ChatPromptTemplate.from_messages([SystemMessagePromptTemplate.from_template(sys_prompt), 
                                               MessagesPlaceholder(variable_name=rand_key), 
                                               HumanMessagePromptTemplate.from_template("{text}")])    
    
    conversation = LLMChain(llm=llm, prompt=prompt, memory=memory)
    return conversation


@app.route('/')
def index():
    return render_template('index3.html')

@app.route('/chat_nu', methods=['POST'])
def chat_nu():
    data = request.get_json()
    user_message = data['text']

    # Generate a unique identifier for each user
    user_id = request.remote_addr + str(request.user_agent)
    if user_id not in user_states:
        user_states[user_id] = {
            'collected_details': [],
            'memory': ConversationBufferMemory(memory_key=rand_key, return_messages=True)
        }

    # Use the user's state instead of the global state
    collected_details = user_states[user_id]['collected_details']
    memory = user_states[user_id]['memory']

    # global collected_details

    conversation = ask_ai(memory)

    # Check if user message is a detail and it's not collected yet
    if user_message.lower() in ["name", "age", "email", "children", "phone number"] and user_message.lower() not in collected_details:
        memory.chat_memory.add_system_message(SystemMessage("I've noted that you're providing your {}.".format(user_message)))
        collected_details.append(user_message.lower())  # Add collected detail to the list
    else:
        memory.chat_memory.add_user_message(user_message)

    response = conversation.invoke({"text": user_message})

    # If all details are collected, reset the collected_details list
    if all(detail in collected_details for detail in ["name", "age", "email", "children", "phone number"]):
        collected_details = []


    # Todo: Guide Visitors through our servive options    

    return jsonify({'response': response['text']})
    


@app.route('/chat_ru', methods=['POST'])
def chat_ru():
    data = request.get_json()
    user_message = data['text']

    return jsonify({'response': f'welcome back {user_message}'})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
