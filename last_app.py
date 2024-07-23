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
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Configuration for SQLAlchemy and SQLite
postgres = ("postgresql://user_details_haex_user:3aK54eW8gVFodhyKNcVH5AE59wp2ietV@dpg-cpepfp7sc6pc73a1m9i0-a.oregon"
            "-postgres.render.com/user_details_haex")

pg2 = ("postgresql://avnadmin:AVNS_UfEmJtUzKREg8ZI8OSV@pg-5fa3219-timcodedata-131f.c.aivencloud.com:13352/defaultdb"
       "?sslmode=require")
app.config['SQLALCHEMY_DATABASE_URI'] = pg2  # 'sqlite:///user_details.db'
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
    npid = db.Column(db.String(100))
    home_address = db.Column(db.String(100))
    surname = db.Column(db.String(100))
    birth_date = db.Column(db.String(100))


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
        llm = ChatOpenAI(model='gpt-4-turbo-2024-04-09',  # gpt-4o-2024-05-13
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
    return data


def create_self_patient(name, phone, email_addr, full_birthdate, house_address, last_name):
    url = "https://api.au1.cliniko.com/v1/patients"
    name = str(name)
    full_birthdate = str(full_birthdate)
    phone = str(phone)
    email_addr = str(email_addr)
    house_address = str(house_address)
    last_name = str(last_name)

    payload = {
        "accepted_privacy_policy": True,
        "accepted_email_marketing": True,
        "address_1": f"{house_address}",
        "country": "United Kingdom",
        "date_of_birth": f"{full_birthdate}",
        "email": f"{email_addr}",
        "first_name": f"{name}",
        "last_name": f"{last_name}",
        "receives_confirmation_emails": True,
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
    return data


def create_new_appt(patient_id, appt_type='initial consult', appt_id="60586", practitioner_id='22152'):
    appt_url = "https://api.au1.cliniko.com/v1/individual_appointments"
    if appt_type == "initial consult":
        appt_id = "60586"
    elif appt_type == "intro phone call":
        appt_id = '1215064152993695622'
    start_date = datetime.today().strftime('%Y-%m-%d')
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json',
    }
    appt_payload = {
        "appointment_type_id": f"{appt_id}",
        "business_id": "15310",
        # "ends_at": "2019-08-24T14:15:22Z",
        # "notes": "string",
        "patient_id": patient_id,  # '1427472976856483735',  # f"{new_patient_data['id']}",
        # "patient_case_id": "1",
        "practitioner_id": f'{practitioner_id}',
        "starts_at": start_date,
        # "repeat_rule": {
        #   "number_of_repeats": 0,
        #   "repeat_type": "Daily",
        #   "repeating_interval": 0
        # }
    }

    appt_response = requests.post(appt_url, json=appt_payload, headers=headers)

    appt_data = appt_response.json()
    return appt_data


@app.route('/')
def index():
    return render_template('index_last.html')


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
                'collected_details3': {},
                'memory': ConversationBufferMemory(memory_key=rand_key, return_messages=True),
                'last_question': None,
                'details_collected': False,  # Flag to check if details have already been collected
                'details_collected2': False,
                'details_collected3': False
            }

        # Use the user's state instead of the global state
        user_state = user_states[user_id]
        collected_details = user_state['collected_details']
        collected_details3 = user_state['collected_details3']
        collected_details2 = user_state['collected_details2']
        memory = user_state['memory']

        conversation = ask_ai(memory, 'conv.txt', 'gpt-4o-2024-05-13',
                              llm_type=0)  # gpt-4o-2024-05-13 # gpt-4-turbo-2024-04-09

        # Add a user message to the memory
        memory.chat_memory.add_user_message(user_message)

        # Define details we want to collect
        details_to_collect = ["name", "age", "email", "children", "phone number"]
        details_to_collect3 = ['birth date', 'home address', 'surname']
        details_to_collect2 = ["child's first name", "last name", "gender", "home address",
                               "date of birth", 'heard about us']

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

        # collect add info
        if last_question and last_question in details_to_collect3:
            # Extract detail type from the last question
            detail_type = last_question
            collected_details3[detail_type] = clean_input(user_message, llm_type=0)
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
                if len(collected_details2) == 6:
                    break
        # Determine if the bot's response is asking for a additional specific user detail
        for detail3 in details_to_collect3:
            if detail3 in response_text.lower():
                user_state['last_question'] = detail3
                if len(collected_details3) == 3:
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

        print('col details 1', collected_details)

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
                phone = collected_details["phone number"]
                # print(child_fn, child_ln, child_gender, child_addr, child_dob, email_addr, phone, referral_source)
                try:
                    # (child_fn, child_ln, child_gender, child_addr, phone, child_dob, email_addr, referral_source
                    print('sending collected details: ', child_fn, child_ln, child_gender, child_addr, child_dob,
                          email_addr, referral_source, phone)
                    new_pat = create_new_patient(child_fn, child_ln, child_gender, child_addr, phone,
                                                 child_dob, email_addr, referral_source)

                    npid = new_pat['id']
                    new_appt = create_new_appt(npid)
                    self_lnk = new_appt['links']['self']

                    # Update the UserDetail with the new patient ID (npid)
                    user_detail = UserDetail.query.filter_by(email=email_addr).first()
                    if user_detail:
                        user_detail.npid = npid
                        db.session.commit()
                        print(f'Updated user {user_detail.name} with new patient ID {npid} and appt link {self_lnk}')
                except Exception as e:
                    print(e)
                    import traceback
                    traceback.print_exc()

        print('col details 2', collected_details2)

        # If all details are collected, set the flag and save to the database
        if all(detail in collected_details3 for detail in details_to_collect3) or len(collected_details3) == 3:
            if not user_state['details_collected3']:  # Check if details are already collected
                user_state['details_collected3'] = True  # Set the flag to True
                print('finished collecting additional details', collected_details3)

                try:
                    # (name, phone, email_addr, full_birthdate, house_address, last_name):
                    new_pat = create_self_patient(name=collected_details['name'],
                                                  phone=collected_details['phone number'],
                                                  email_addr=collected_details['email'],
                                                  full_birthdate=collected_details3['birth date'],
                                                  house_address=collected_details3['home address'],
                                                  last_name=collected_details3['surname'])

                    npid = new_pat['id']
                    if "introductory phone call" in user_message:
                        appt_type = 'intro phone call'
                    else:
                        appt_type = 'initial consult'
                    new_appt = create_new_appt(npid, appt_type)
                    self_lnk = new_appt['links']['self']
                    # Update the UserDetail with the new patient ID (npid)
                    user_detail = UserDetail.query.filter_by(email=collected_details['email']).first()
                    if user_detail:
                        user_detail.npid = npid
                        user_detail.home_address = collected_details3['home address']
                        user_detail.surname = collected_details3['surname']
                        user_detail.birth_date = collected_details3['birth date']
                        db.session.commit()
                        print(f'Updated user {user_detail.name} with new patient ID {npid} and appt link {self_lnk}')
                except Exception as e:
                    print(e)
                    import traceback
                    traceback.print_exc()

        print('col details 3', collected_details3)

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


user_detail_cache = None


def check_for_appt_type(msg):
    llm = ChatOpenAI(model='gpt-4-turbo-2024-04-09',  # gpt-4o-2024-05-13
                     openai_api_key="sk-proj-FBjqom2m67JasQzCTfxhT3BlbkFJ8gt1lQAZDCKwv6Q3VOMe")
    memory = ConversationBufferMemory(memory_key="get_apt_type", return_messages=True)
    sys_prompt = f"""The user says: "{msg}", Just incase the text is long and not straightforward, Look for the main 
    information in the user's input and extract it. main information is exactly anyone from this list of therapies:
        1. Retained Reflex Review (RRR)
        2. Retained Reflex Review and Auditory 
        3. DMP Session at CDC
        4. DMP Session Online 
        5. Online Retained Reflex Review, 
    so just scan the user's text and figure out which appointment they're trying to
    book, and return exactly the keyword from the list provided. for example user might mention just Retained Reflex,
    ask them if it's either Retained Reflex Review (RRR) or Retained Reflex Review and Auditory. and return the exact 
    keyword for one with they want.
    also if they just choose DMP Session, ask them if either DMP Session CDC or DMP Session Online , if they choose DMP
    session at CDC , then return DMP Session at CDC as the keyword.
    """
    prompt = ChatPromptTemplate.from_messages([SystemMessagePromptTemplate.from_template(sys_prompt),
                                               MessagesPlaceholder(variable_name="get_apt_type"),
                                               HumanMessagePromptTemplate.from_template("{msg}")])
    conversation = LLMChain(llm=llm, prompt=prompt, memory=memory)

    memory.chat_memory.add_user_message(msg)
    response = conversation.invoke({"text": msg})
    print("entity", response['text'])
    return response['text']
    pass


@app.route('/chat_ru', methods=['POST'])
def chat_ru():
    global user_detail_cache
    try:
        data = request.get_json()
        user_message = data['text']

        # Extract the name (assuming the user input is in the format like 'Tim#1038')
        user_name = user_message.strip()

        # Query the database for the user with the provided name
        # user_detail = UserDetail.query.filter_by(email=user_name).first()
        if not user_detail_cache:
            user_detail_cache = UserDetail.query.filter_by(email=user_name).first()

        # url = "https://api.au1.cliniko.com/v1/appointment_types"
        # headers = {
        #     # Add your required headers here, for example:
        #     'Authorization': f'Basic {encoded_credentials}',
        #     'Content-Type': 'application/json',
        # }
        # query = {
        #     "order": "asc",
        #     # "page": "110",
        #     # "per_page": "10",
        #     # "q[]": "string",
        #     # "sort": "created_at:desc"
        # }
        # response = requests.get(url, params=query, headers=headers)
        #
        # data = response.json()
        data = [{'name': "Retained Reflex Review", 'id': '60585', 'category': 'Retained Reflex Therapy'},
                {'name': "Retained Reflex Review and Auditory", 'id': '60591', 'category': 'Retained Reflex Therapy'},
                {'name': "DMP Session at CDC", 'id': '516802', 'category': 'Psychotherapy'},
                {'name': "DMP Session Online", 'id': '516804', 'category': 'Psychotherapy'},
                {'name': "Online Retained Reflex Review", 'id': '459735', 'category': 'Retained Reflex Therapy'}]
        # print('url', url)
        # print('appt data', data)

        init_message = " "
        appt_message = " "
        add_details_prmt = " "
        print(user_message)
        user_data_got = None

        # if user_detail:
        #     # If the user exists, return their details
        #     user_data = {
        #         # 'id': user_detail.id,
        #         # 'user_id': user_detail.user_id,
        #         'name': user_detail.name,
        #         'age': user_detail.age,
        #         'email': user_detail.email,
        #         'children': user_detail.children,
        #         'phone_number': user_detail.phone_number
        #     }

        npid_ = False

        if user_detail_cache:
            print(user_detail_cache.npid)
            # If the user exists, return their details
            user_data = {
                # 'id': user_detail_cache.id,
                # 'user_id': user_detail_cache.user_id,
                'name': user_detail_cache.name,
                'age': user_detail_cache.age,
                'email': user_detail_cache.email,
                'children': user_detail_cache.children,
                'phone_number': user_detail_cache.phone_number
            }
            npid_ = True if user_detail_cache.npid else False
            try:
                user_data_got = (", ".join([f"'{key}': '{value}'" for key, value in user_data.items()]))
            except:
                pass

            # init_message = f"here are my details {user_data.items()}, let's continue/proceed!"
        # else:
        #     if user_detail is None:
        #         init_message = (f"user message {user_name} does not exist, ignore the rest of the message, and return"
        #                         f"just that")

        # print(init_message)
        for appts in data:
            # print(appts)
            if user_message in appts['name']:
                appt_id = (appts['id'])
                print('appt found', appt_id)
                print(user_detail_cache.npid)
                try:
                    # create new patient
                    # (name, phone, email_addr, full_birthdate, house_address, last_name)
                    if not npid_:
                        print('user wants appt 2, but details incomplete')
                        # add_details_prmt = """Ask for more additional details: NOTE: make sure this exact
                        # sentence/words are in the questions you would be asking one after the other, cos the keywords
                        # would be needed in the Python code - surname - full birth date in this format "YYYY-MM-DD" -
                        # home address
                        #
                        #      ** Never list all of those details for them at once, just ask one after the other,
                        #      without mentioning something like: To proceed with the booking, I'll need a few more
                        #      details from you: 1. **Home address** 🏡 2. **Full birth date** in this format
                        #      "YYYY-MM-DD" 🎂 3. **Surname** 📛 Could you please provide these details one by one?
                        #      just do it like this instead: To proceed with the booking, I'll need a few more details
                        #      from you, could you please provide your surname? once they provide it, then proceed to
                        #      next detail... after collecting all....
                        #
                        # """
                        add_details_prmt = f"""Let the users know that they do not have the access to make {user_message}
                        appointment type yet, they need too go back to the new user section and book an initial
                         consultation appointment before they're able to proceed with other appointment types..
                         In whatever case, if they're interested in booking the intial consultation appointment, 
                         ask them to either refresh or go back to the new user section in the front page of the bot.
                         if they don't want to, ask them if there's anything you can help them with, if there's nothing,
                         nicely end the conversation, else.. proceed to taking care of their questions
                        """
                    new_pat = create_self_patient(name=user_detail_cache.name,
                                                  full_birthdate=user_detail_cache.birth_date,
                                                  email_addr=user_detail_cache.email,
                                                  phone=user_detail_cache.phone_number,
                                                  house_address=user_detail_cache.home_address,
                                                  last_name=user_detail_cache.surname)
                    # create new appt
                    appt_type = appts['category']
                    # patient_id, appt_type='initial consult', appt_id="60586", practitioner_id='22152'
                    new_appt = create_new_appt(patient_id=new_pat['id'], appt_type=appt_type, appt_id=appt_id)
                    if new_appt:
                        print(f'Updated {user_detail_cache.name} to appt type {appt_type}')

                        appt_prmt = (f"new user has made {user_message} kind of appointment, greet and ask if there's "
                                     f"anything else you can help them with, if NO, end the convo, if YES, proceed to "
                                     f"help them more, based on the whole system prompt")
                        appt_message = appt_prmt
                    break
                except Exception as e:
                    print(e)
                    import traceback
                    traceback.print_exc()
        sys_prmt = \
            f"""- **Objective:** You're a CDC bot, you already talked to users and collected all their information,
            Let returning users know that you're CDC BOT Assistant named Amara, you're available to Support users and
            their families on their journey, providing information and tailored assistance, based on their info.. **
            don't ask them to confirm their info, unless they input their email and if it's found! ** if you get any
            greetings message like Hi, Hey, Hola.. still let them know they need to input their email address so you
            can check if you have their info ** Use as much emoji as you can, just to make sure, you're friendly and
            polite enough to them, as a returning user ** if their phone number is empty, just let them know it's
            empty, don't come up with random numbers!! ** Never tell them to Please wait a moment to check if you
            have their details or anything similar, just directly tell them if you have it or not. ** if user details
            is not found, don't make up anything and just return to them that it's not found!!

            - Here's the Users Details {user_data_got},
                if user data is empty or none, let them know you cannot find their details in our record, else
                 if their detail is correct and there are no missing details, Greet them properly!, and list their
                info for them to crosscheck: Hey [their info details, such as age, children, phone number], so great to
                see you again (insert name). How's your health been since I saw you last? Include MAYBE AN EMOJI to make
                it lively. wait until you receive another response from them before proceeding to ask questions,
                they might have something to say, so don't be too straightforward with your questions, and make your
                questions as detailed as possible.
                 ** most important part, never ask them to hold on that you're checking for their details or similar sentence,
                  just let them know immediately they input their email address so you

                - Do not ever repeat the output response again... Just focus on Proceeding, make sure you're able to
                handle any form of convo!
                
                *** Politely ask them if they want to make another appointment or there's something after figuring out if they're fine, so you need to check if they're fine before proceeding to new appointment section.
                    if they want another appointment, then proceed to next like, you just need to confirm that they want another appointment before you proceed to list the available appointments for them,

                 - If they want another appointment, Then Proceed:
                
                     if Users in inputs positive response that they want new appointment:
                        ask them what type of appointment would they like to make from the list below and briefly explain to them what they are:
                            ** the appointment category is to be used for basic explanation, tell them to please choose from the list of available appointments
                            [
                                ('appointment name: ', 'Retained Reflex Review (RRR)', 
                                    'appointment category: ', 'Retained Reflex Therapy'),        
                                ('appointment name: ', 'Retained Reflex Review and Auditory',
                                        'appointment category: ', 'Retained Reflex Therapy'),
                                ('appointment name: ', 'D.M.P. Session @ CDC, SW11',
                                        'appointment category: ', 'Psychotherapy'),
                                ('appointment name: ', 'D.M.P. Session - Online', 
                                        'appointment category: ', 'Psychotherapy'),
                                ('appointment name: ', 'Online Retained Reflex Review',
                                    'appointment category: ', 'Retained Reflex Therapy',)
                            ]
                            
            "Retained Reflex Review (Online)": 459735

              if they choose to do any of the above, then proceed to ask them for their personal details:
                # retrieve their basic details
                # ask more details.
    

                if users inputs No, ask them... how you can help them? Just do not return their details again, after the first time..
            """

        # Generate a unique identifier for each user
        # print('code reach here 1')
        full_msg = sys_prmt + "\n" + add_details_prmt  # init_message + "\n" + sys_prmt + "\n" + add_details_prmt
        if appt_message != " ":
            full_msg = full_msg + "\n" + appt_message
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
        # print('code reach here 2')

        response = conversation.invoke({"text": str(user_message)})
        response_text = response['text']

        return jsonify({'response': response_text})

    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()
        return jsonify({'response': str(e)})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)
