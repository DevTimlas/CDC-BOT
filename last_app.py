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
import base64
import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

app = Flask(__name__)
CORS(app)

# Configuration for SQLAlchemy and SQLite
postgres = ("postgresql://user_details_haex_user:3aK54eW8gVFodhyKNcVH5AE59wp2ietV@dpg-cpepfp7sc6pc73a1m9i0-a.oregon"
            "-postgres.render.com/user_details_haex")
app.config['SQLALCHEMY_DATABASE_URI'] = postgres # 'sqlite:///user_details.db'  # postgres
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


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
user_states1 = {}
rand_key = str(uuid.uuid4())


def ask_ai(memory, sys_prompt_file, model_type, llm_type=0):
    if llm_type == 0:
        llm = ChatOpenAI(temperature=0, openai_api_key="sk-proj-FBjqom2m67JasQzCTfxhT3BlbkFJ8gt1lQAZDCKwv6Q3VOMe",
                         model=model_type)  # -turbo-2024-04-09 max_tokens=3095
    elif llm_type == 1:
        llm = ChatGroq(temperature=0, model="llama3-70b-8192",
                       api_key="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")
    else:
        raise Exception("Invalid llm type")

    # sys_prompt = open('conv.txt', 'r').read().strip()
    sys_prompt = open(sys_prompt_file, 'r').read().strip()
    prompt = ChatPromptTemplate.from_messages([SystemMessagePromptTemplate.from_template(sys_prompt),
                                               MessagesPlaceholder(variable_name=rand_key),
                                               HumanMessagePromptTemplate.from_template("{text}")])

    conversation = LLMChain(llm=llm, prompt=prompt, memory=memory)
    return conversation


# def chat_returning_user(memory):
#     llm = ChatOpenAI(temperature=0, openai_api_key="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",
#                      model='gpt-4')  # -turbo-2024-04-09 max_tokens=3095
#     sys_prompt = open('conv_rtn.txt', 'r').read().strip()
#     prompt = ChatPromptTemplate.from_messages([SystemMessagePromptTemplate.from_template(sys_prompt),
#                                                MessagesPlaceholder(variable_name=rand_key),
#                                                HumanMessagePromptTemplate.from_template("{text}")])
#
#     conversation = LLMChain(llm=llm, prompt=prompt, memory=memory)
#     return conversation


def clean_input(text, llm_type=0):
    if llm_type == 0:
        llm = ChatOpenAI(temperature=0.2, model='gpt-4',
                         openai_api_key="sk-proj-FBjqom2m67JasQzCTfxhT3BlbkFJ8gt1lQAZDCKwv6Q3VOMe")
    elif llm_type == 1:
        llm = ChatGroq(temperature=0, model="llama3-70b-8192",
                       api_key="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")
    else:
        raise Exception("Invalid llm type for cleaning text...")
    memory = ConversationBufferMemory(memory_key="clean_msg", return_messages=True)
    sys_prompt = """The user says: "{text}", Just incase the text is long and not straightforward, Look for the main 
    information in the user's input and extract it.. for example if they say I am 39, it means we're asking for their 
    age, so just return the 39. for example if they say my name is Joe, it means we're asking for their name, 
    so just return the Joe - if a user enters something like tim, return this instead Tim, make sure user's name 
    always starts with capital letters - If they're telling you about the number of children they have, like 0,1,2,3,
    4,5,6,7,8,9,... just find the number in their text and extract and return it.. - if it is their name, 
    make sure you return the exact name  - if user message doesn't contain any specific information that you 
    can extract, just return exactly what they input. - Also, a text might look like this: * Thank you for providing 
    your child's date of birth! Next, could you please share with me your child's contact number? This will help us 
    keep in touch regarding the consultation details. 📞.'* --Therefore, you are required to only extract and return 
    the keyword "child's contact number". - if they add a punctuation at the end of their details example 3' or 
    John*, remove it and return modified one which is 3 or John. 
    - if they're inputting their email as in this pattern; xxx@yyy.zzz, you should return it exactly the way they input it.
                      
    """
    prompt = ChatPromptTemplate.from_messages([SystemMessagePromptTemplate.from_template(sys_prompt),
                                               MessagesPlaceholder(variable_name="clean_msg"),
                                               HumanMessagePromptTemplate.from_template("{text}")])
    conversation = LLMChain(llm=llm, prompt=prompt, memory=memory)

    memory.chat_memory.add_user_message(text)
    response = conversation.invoke({"text": text})
    print("entity", response['text'])
    return response['text']


username = 'MS0xNDIzODc4MjMzNzQ4NjcwNDI0LTZUTUhkd3JUcDQzVVh0K1MwZ2xJMHQveEI5cTJRZmYz-au1'
password = ''
credentials = f'{username}:{password}'
encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')


def create_new_patient(child_fn, child_ln, child_gender, child_addr, phone, child_dob, email_addr, referral_source):
    url = "https://api.au1.cliniko.com/v1/patients"
    child_fn = str(child_fn)
    child_ln = str(child_ln)
    # child_age = str(child_age)
    child_gender = str(child_gender)
    child_addr = str(child_addr)
    phone = str(phone)
    child_dob = str(child_dob)
    email_addr = str(email_addr)
    referral_source = str(referral_source)

    payload = {
        "accepted_privacy_policy": True,
        "accepted_email_marketing": True,
        "address_1": f"{child_addr}",
        "country": "United Kingdom",
        "date_of_birth": f"{child_dob}",
        "email": f"{email_addr}",
        "first_name": f"{child_fn}",
        "gender_identity": f"{child_gender}",
        "last_name": f"{child_ln}",
        "receives_confirmation_emails": True,
        "referral_source": f"{referral_source}",
        # "time_zone": "United Kingdom",
        "unsubscribe_sms_marketing": True,
        "patient_phone_numbers": [
            {
                "phone_type": "Mobile",
                "number": f"{phone}"
            }
        ]
    }

    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json',
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response)

    data = response.json()
    return (data)


@app.route('/')
def index():
    return render_template('index8.html')


@app.route('/chat_nu', methods=['POST'])
def chat_nu():
    data = request.get_json()
    user_message = data['text']

    # Generate a unique identifier for each user
    try:
        user_id = request.remote_addr + str(request.user_agent)
        if user_id not in user_states:
            user_states[user_id] = {
                'collected_details': {},
                'collected_details2': {},
                'memory': ConversationBufferMemory(memory_key=rand_key, return_messages=True),
                'last_question': None,
                'details_collected': False,  # Flag to check if details have already been collected
                'details_collected2': False
            }

        # Use the user's state instead of the global state
        user_state = user_states[user_id]
        collected_details = user_state['collected_details']
        collected_details2 = user_state['collected_details2']
        memory = user_state['memory']

        conversation = ask_ai(memory, 'conv.txt', 'gpt-4-turbo-2024-04-09', llm_type=0)

        # Add user message to the memory
        memory.chat_memory.add_user_message(user_message)

        # Define details we want to collect
        details_to_collect = ["name", "age", "email", "children", "phone number"]
        details_to_collect2 = ["child's first name", "last name", "gender", "home address",
                               "contact number", "date of birth", 'heard about us']

        # Check if the last question asked by the bot is about a specific detail
        last_question = user_state['last_question']
        print(last_question)
        if last_question and last_question in details_to_collect:
            # Extract detail type from the last question
            detail_type = last_question
            collected_details[detail_type] = clean_input(user_message, llm_type=0)
            user_state['last_question'] = None  # Reset last_question after capturing the response

        # collect child info
        if last_question and last_question in details_to_collect2:
            # Extract detail type from the last question
            detail_type = last_question
            collected_details2[detail_type] = clean_input(user_message, llm_type=0)
            user_state['last_question'] = None  # Reset last_question after capturing the response

        # Get response from the AI
        response = conversation.invoke({"text": user_message})
        response_text = response['text']

        # Determine if the bot's response is asking for a specific user detail
        for detail in details_to_collect:
            if detail in response_text.lower():
                user_state['last_question'] = detail
                if len(collected_details) == 5:
                    break

        # Determine if the bot's response is asking for a specific child detail
        for detail2 in details_to_collect2:
            if detail2 in response_text.lower():
                user_state['last_question'] = detail2
                if len(collected_details2) == 8:
                    break

        # If all details are collected, set the flag and save to the database
        if all(detail in collected_details for detail in details_to_collect) or len(collected_details) == 5:
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

        # If all details are collected, set the flag and save to the database
        if all(detail2 in collected_details2 for detail2 in details_to_collect2):
            if not user_state['details_collected2']:  # Check if details are already collected
                user_state['details_collected2'] = True  # Set the flag to True
                print('finished collecting child details', collected_details2)
                # Extract values
                child_fn = collected_details2["child's first name"]
                child_ln = collected_details2["last name"]
                child_gender = collected_details2["gender"]
                child_addr = collected_details2["home address"]
                child_dob = collected_details2["date of birth"]
                email_addr = collected_details["email"]  # collected_details2["child's email"]
                referral_source = collected_details2["heard about us"]
                phone = collected_details2["contact number"]
                # print(child_fn, child_ln, child_gender, child_addr, child_dob, email_addr, phone, referral_source)
                try:
                    new_pat = create_new_patient(child_fn, child_ln, child_gender, child_addr, phone, child_dob,
                                                 email_addr,
                                                 referral_source)
                    print('success', new_pat)
                except Exception as e:
                    print(e)
                    pass

        print(collected_details2)

        # # if good client
        # # create new patient
        # if ((("consultation" in user_message) or ("consultation" in response_text)) or
        #         (('appointment' in user_message) or ('appointment' in response_text))):
        #     print(True)

        # new_patient_data = create_new_patient(child_fn_t, child_ln_t, child_gender_t, child_addr_t, phone_t,
        #                                       child_dob_t, email_addr_t, referral_source_t)
        # return jsonify({"response", new_patient_data})

        # if ("consultation" or "appointment" in user_message) or ("consultation" or "appointment" in response_text):
        #     pass
        #
        #     # ask if user would like to book an appointment/consultation:
        #     # if yes, click on yes button
        #     # ask info
        #     # book appt

        return jsonify({'response': response_text})
    except Exception as e:
        print(e)
        pass


@app.route('/chat_ru', methods=['POST'])
def chat_ru():
    try:
        data = request.get_json()
        user_message = data['text']

        # Extract the name (assuming the user input is in the format like 'Tim#1038')
        user_name = user_message.strip()

        # Query the database for the user with the provided name
        user_detail = UserDetail.query.filter_by(email=user_name).first()

        init_message = " "
        print(user_message)

        if user_detail:
            # If the user exists, return their details
            user_data = {
                # 'id': user_detail.id,
                # 'user_id': user_detail.user_id,
                'name': user_detail.name,
                'age': user_detail.age,
                'email': user_detail.email,
                'children': user_detail.children,
                'phone_number': user_detail.phone_number
            }

            print(user_data)

            init_message = f"here are my details {user_data.items()}, let's continue/proceed!"
        # else:
        #     if user_detail is None:
        #         init_message = (f"user message {user_name} does not exist, ignore the rest of the message, and return "
        #                         f"just that")

        print(init_message)
        sys_prmt =\
            """- **Objective:** You're a CDC bot, you already talked to users and collected all their information, 
            Let returning users know that you're CDC BOT Assistant named Amara, you're available to Support users and 
            their families on their journey, providing information and tailored assistance, based on their info.. ** 
            don't ask them to confirm their info, unless they input their email and if it's found! ** if you get any 
            greetings message like Hi, Hey, Hola.. still let them know they need to input their email address so you 
            can check if you have their info ** Use as much emoji as you can, just to make sure, you're friendly and 
            polite enough to them, as a returning user ** if their phone number is empty, just let them know it's 
            empty, don't come up with random numbers!! ** Never tell them to Please wait a moment to check if you 
            have their details or anything similar, just directly tell them if you have it or not. ** if user details 
            is not found, don't make up anything and just return to them that it's not found!!

                - Here's the Users Details "user_data", if their details is correct, Greet them properly!, and list their 
                info for them to crosscheck: Hey [their info details, such as age, children, phone number], so great to 
                see you again (insert name). How's your health been since I saw you last? Include MAYBE AN EMOJI to make 
                it lively. wait until you receive another response from them before proceeding to ask questions, 
                they might have something to say, so don't be too straightforward with your questions, and make your 
                questions as detailed as possible.
    
                - Do not ever repeat the output response again... Just focus on Proceeding, make sure you're able to 
                handle any form of convo!
    
                 - Then Proceed to ask if they want to schedule another appointment of type 2
    
                     if Users in inputs Yes, tell them the feature is coming soon,
    
                     if users inputs No, ask them... how you can help them? Just do not return their details again, 
                     after the first time..

            """

        # Generate a unique identifier for each user
        full_msg = init_message + "\n" + sys_prmt
        # del init_message
        user_id = request.remote_addr + str(request.user_agent)
        if user_id not in user_states1:
            user_states1[user_id] = {
                'memory': ConversationBufferMemory(memory_key=rand_key, return_messages=True),
            }

        # Use the user's state instead of the global state
        user_state = user_states1[user_id]
        memory = user_state['memory']

        prompt = ChatPromptTemplate.from_messages([SystemMessagePromptTemplate.from_template(full_msg),
                                                   MessagesPlaceholder(variable_name=rand_key),
                                                   HumanMessagePromptTemplate.from_template("{text}")])
        llm = ChatOpenAI(temperature=0.2, model='gpt-4',
                         openai_api_key="sk-proj-FBjqom2m67JasQzCTfxhT3BlbkFJ8gt1lQAZDCKwv6Q3VOMe")

        conversation = LLMChain(llm=llm, prompt=prompt, memory=memory)

        # Add user message to the memory
        memory.chat_memory.add_user_message(str(user_message))

        response = conversation.invoke({"text": str(user_message)})
        response_text = response['text']

        return jsonify({'response': response_text})

    except Exception as e:
        print(e)
        return jsonify({'response': str(e)})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
