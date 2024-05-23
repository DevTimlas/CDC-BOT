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
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
CORS(app)

# Configuration for SQLAlchemy and SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_details.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# ### Collecting User Details:
# 1. **Name**: "Can I have your name? Please include a unique tag like joe#1234."
# 2. **Age**: "May I ask your age?"
# 3. **Email**: "Could you provide your email address?"
# 4. **Children**: "Do you have children? How many?"
# 5. **Phone Number**: "What’s your phone number?"


# Define the UserDetail model
class UserDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # user_id = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(100))
    age = db.Column(db.String(10))
    email = db.Column(db.String(100))
    children = db.Column(db.String(10))
    phone_number = db.Column(db.String(20))


# Ensure tables are created within the application context
with app.app_context():
    db.create_all()

user_states = {}
rand_key = str(uuid.uuid4())


def ask_ai(memory):
    llm = ChatOpenAI(temperature=0, openai_api_key="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",
                     max_tokens=3095, model='gpt-4')  # -turbo-2024-04-09

    sys_prompt = open('conv.txt', 'r').read().strip()
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
            'collected_details': {},
            'memory': ConversationBufferMemory(memory_key=rand_key, return_messages=True),
            'last_question': None,
            'details_collected': False  # Flag to check if details have already been collected
        }

    # Use the user's state instead of the global state
    user_state = user_states[user_id]
    collected_details = user_state['collected_details']
    memory = user_state['memory']

    conversation = ask_ai(memory)

    # Add user message to the memory
    memory.chat_memory.add_user_message(user_message)

    # Define details we want to collect
    details_to_collect = ["name", "age", "email", "children", "phone number"]

    # Check if the last question asked by the bot is about a specific detail
    last_question = user_state['last_question']
    print(last_question)
    if last_question and last_question in details_to_collect:
        # Extract detail type from the last question
        detail_type = last_question
        collected_details[detail_type] = user_message
        user_state['last_question'] = None  # Reset last_question after capturing the response

    # Get response from the AI
    response = conversation.invoke({"text": user_message})
    response_text = response['text']

    # Determine if the bot's response is asking for a specific detail
    for detail in details_to_collect:
        if detail in response_text.lower():
            user_state['last_question'] = detail
            if len(collected_details) == 5:
                break

    # If all details are collected, set the flag and save to the database
    if all(detail in collected_details for detail in details_to_collect):
        if not user_state['details_collected']:  # Check if details are already collected
            user_state['details_collected'] = True  # Set the flag to True
            print('finished collecting details', collected_details)

            # Save the collected details to the database
            user_detail = UserDetail(
                # user_id=user_id,
                name=collected_details.get('name'),
                age=collected_details.get('age'),
                email=collected_details.get('email'),
                children=collected_details.get('children'),
                phone_number=collected_details.get('phone number')
            )
            db.session.add(user_detail)
            db.session.commit()

    print(collected_details)

    return jsonify({'response': response_text})


@app.route('/chat_ru', methods=['POST'])
def chat_ru():
    data = request.get_json()
    user_message = data['text']

    # Extract the name (assuming the user input is in the format like 'Tim#1038')
    user_name = user_message.strip()

    # Query the database for the user with the provided name
    user_detail = UserDetail.query.filter_by(name=user_name).first()

    if user_detail:
        # If the user exists, return their details
        user_data = {
            'id': user_detail.id,
            # 'user_id': user_detail.user_id,
            'name': user_detail.name,
            'age': user_detail.age,
            'email': user_detail.email,
            'children': user_detail.children,
            'phone_number': user_detail.phone_number
        }
        print(user_data)
        return jsonify({'response': user_data})
    else:
        # If the user does not exist, return an error message
        return jsonify({'response': f'User {user_name} not found'}), 404


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
