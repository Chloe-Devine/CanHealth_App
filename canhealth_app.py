import streamlit as st
import pandas as pd
print('loading function')
import canhealth_functions
import llm_setup_runpod as llm
from datetime import datetime
import threading
import base64
import requests
from io import StringIO
import json
import os
import time



sample_df = pd.read_excel('data/samples/sample_dataset.xlsx',engine='openpyxl')
sample_df = sample_df[sample_df['use'].notna()]
sample_dict = dict(zip(sample_df['Requested Exam'], sample_df['Indication']))


sample_selection = list(sample_dict.keys())
sample_selection.append('New Indication')

assistant_avatar= 'SAPIEN-SECCURE-ICON-LOGO-COLOR.png'
# -----------------------------
# PAGE CONFIG — must come first
# -----------------------------
st.set_page_config(
    page_title="Sapien US Protocoling",
    page_icon="SAPIEN-SECCURE-ICON-LOGO-COLOR.png",
    layout="wide"
)


# Inject custom CSS to set the width of the sidebar
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 1000px !important; # Set the width to your desired value
        }
    </style>
    """,
    unsafe_allow_html=True,
)

def append_feedback_to_github(feedback_data):
    token = st.secrets["github"]["token"]
    repo = st.secrets["github"]["repo"]
    path = "data/prediction_feedback.csv"  # change if your CSV is elsewhere

    headers = {"Authorization": f"token {token}"}
    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    # Check if file exists
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        # File exists → decode and append
        resp_json = resp.json()
        sha = resp_json["sha"]
        content = base64.b64decode(resp_json["content"]).decode()
        df = pd.read_csv(StringIO(content))
        df = pd.concat([df, pd.DataFrame([feedback_data])], ignore_index=True)
    else:
        # File does not exist → create new DataFrame
        df = pd.DataFrame([feedback_data])
        sha = None

    # Encode CSV to base64 for GitHub
    csv_str = df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_str.encode()).decode()

    # Prepare payload for GitHub API
    data = {
        "message": f"Add feedback {datetime.now().isoformat()}",
        "content": encoded_content
    }
    if sha:
        data["sha"] = sha  # required if updating

    # Send request to update or create file
    put_resp = requests.put(url, headers=headers, data=json.dumps(data))
    if put_resp.status_code not in [200, 201]:
        st.error(f"❌ Failed to save feedback: {put_resp.text}")
    else:
        st.success("✅ Feedback recorded in GitHub!")

##Additing in credential check###########################################

# def send_sales_email(name, email, message):
#     """Send sales inquiry using SendGrid API."""
#     try:
#         config = st.secrets["email"]
#         api_key = config["sendgrid_api_key"]
#         sender_email = config["sender_email"]
#         sales_email = config["sales_email"]
#
#         data = {
#             "personalizations": [{"to": [{"email": sales_email}]}],
#             "from": {"email": sender_email, "name": "Sapien Billing App"},
#             "subject": "New Access Request – Sapien Billing Intelligence",
#             "content": [
#                 {
#                     "type": "text/plain",
#                     "value": f"Name: {name}\nEmail: {email}\nMessage:\n{message}"
#                 }
#             ],
#         }
#
#         response = requests.post(
#             "https://api.sendgrid.com/v3/mail/send",
#             headers={
#                 "Authorization": f"Bearer {api_key}",
#                 "Content-Type": "application/json"
#             },
#             json=data
#         )
#
#         if response.status_code in (200, 202):
#             st.success("✅ Your message has been sent! Our sales team will contact you soon.")
#         else:
#             st.error(f"❌ Failed to send email (code {response.status_code}): {response.text}")
#
#     except Exception as e:
#         st.error(f"⚠️ Could not send email: {e}")

def check_credentials():
    """Enhanced login with logo, description, and sales contact form."""
    # --- Logo and Title ---
    st.logo(
        "Sapien_Logo_Colour_TransparentBackground_WhiteText.png",
        size = 'large'
    )

    def credentials_entered():
        username = st.session_state["username"]
        password = st.session_state["password"]

        valid_users = st.secrets["credentials"]["users"]
        valid_passwords = st.secrets["passwords"]

        if username in valid_users and password == valid_passwords[username]:
            st.session_state["auth_ok"] = True
            st.session_state["user"] = username
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["auth_ok"] = False
            st.session_state["password"] = ""

    if "auth_ok" not in st.session_state or not st.session_state["auth_ok"]:

        st.markdown(
            """
            <div style='text-align: center;'>
                <h2>Welcome to the Sapien Billing Platform</h2>
                <p style='font-size:16px; color: #d0d0d0;'>
                    Log in to access our billing portal.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password", on_change=credentials_entered)
        if "auth_ok" in st.session_state and not st.session_state["auth_ok"]:
            st.error("😕 Incorrect username or password")


        # --- Divider ---
        st.markdown("---")

        # --- Sales contact section ---
        with st.expander("No login? Contact Us"):
            st.markdown("Fill out this short form and our team will reach out to get you access.")
            name = st.text_input("Your name")
            email = st.text_input("Your email address")
            message = st.text_area("How can we help?")

            if st.button("Send Message"):
                if name and email and message:
                    # send_sales_email(name, email, message)
                    st.warning(".")
                else:
                    st.warning("Please complete all fields before sending.")

        return False

    else:
        return True

if check_credentials():
    st.success(f"Welcome, {st.session_state['user']}! 👋")
    if not st.session_state.get('warmup_done',False):
        print(st.session_state.get('warmup_done'))
        print('warming up')
        threading.Thread(target=llm.warmup_model, args=(st.secrets["runpod_api_key"]["api_key"],)).start()
        print('warmup done')
        st.session_state['warmup_done'] = True



    ###Main App####
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

    if "message_history" not in st.session_state:
        st.session_state["message_history"] = []

    if "exam" not in st.session_state:
        st.session_state['exam'] = False

    if "indication" not in st.session_state:
        st.session_state['indication'] = False

    if "sample_selection" not in st.session_state:
        st.session_state['sample_selection'] = False

    if "run_prompt" not in st.session_state:
        st.session_state['run_prompt'] = False


    if "ai_output" not in st.session_state:
        st.session_state['ai_output'] = False

    if "feedback_history" not in st.session_state:
        st.session_state["feedback_history"] = []

    if "feedback_current" not in st.session_state:
        st.session_state["feedback_current"] = {}

    if "last_message" not in st.session_state:
        st.session_state['last_message'] = False




    # Function for Reset Button
    def reset():
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]
        st.session_state.run_prompt = False
        st.session_state['indication'] = False
        st.session_state['exam'] = False
        st.session_state['sample_selection'] = False
        st.session_state['ai_output'] = False
        st.session_state['feedback_history'] = []
        st.session_state['message_history'] = []





    # Clear function to reset some of the text areas when a new prompt is selected
    def clear():
        st.session_state['indication'] = False
        st.session_state['sample_selection'] = False
        st.session_state['run_prompt'] = False
        st.session_state['exam'] = False



    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message(msg["role"], avatar="🧑‍💻").write(msg["content"])
        else:
            st.chat_message(msg["role"], avatar=assistant_avatar).write(msg["content"])
            # st.chat_message(msg["role"], avatar="🤖").write(msg["content"])

    with st.sidebar:
        st.logo('Sapien_Logo_Colour_TransparentBackground_WhiteText.png',size='large')
        col1, col2, col3= st.columns([2,2,2])
        with col1:
            if st.button('Reset Chat',  use_container_width=True, type = "primary"):
                feedback_data = {
                    "Timestamp": datetime.now().isoformat(),
                    "User": st.session_state.get("user", "anonymous"),
                    "Feedback Type": "Reset History",
                    "Feedback Text": '',
                    "Total History": st.session_state.feedback_history,
                    "Problem Response": 'App Reset',
                    "Current Indication": st.session_state.get("indication"),
                    "Current Exam": st.session_state.get("exam"),
                    "Current AI Output": st.session_state.get("ai_output", "")
                }

                # append_feedback_to_github(feedback_data)
                pd.DataFrame([feedback_data]).to_csv(
                    "data/output/prediction_feedback.csv",
                    mode="a",
                    header=not os.path.exists("data/output/prediction_feedback.csv"),
                    index=False
                )
                reset()
                st.rerun()
        with col2:
            if st.button("Logout",  use_container_width=True,type ="primary"):
                for key in ["auth_ok", "user"]:
                    st.session_state.pop(key, None)
                st.rerun()
        with col3:
            if st.button("Prioritize", use_container_width=True, type="primary"):
                if not st.session_state.exam:
                    st.error('Exam Requested needed')
                if not st.session_state.indication:
                    st.error('Indication needed')
                else:
                    st.session_state.run_prompt = True
                # st.rerun()


        tab1, tab2 = st.tabs(['Prompting', 'Feedback'])
        with tab1:

            # Indication selection dropdown
            st.session_state.sample_selection = st.selectbox('Sample Selection', placeholder='Choose an Exam',
                                                             options=sample_selection,index=None, on_change=clear)

            #For samples, get the indication
            if st.session_state.sample_selection and st.session_state.sample_selection not in ['New Indication']:
                st.session_state.exam = st.session_state.sample_selection
                st.session_state.indication = sample_dict[st.session_state.exam]
                #When sample selected, show the details in text areas and allow user to run with Run Prompt Button
                if st.session_state.exam:
                    st.session_state.exam = st.text_area('Exam Requested', st.session_state.exam)
                    st.session_state.indication = st.text_area('Indication', value=st.session_state.indication)

            #For new indications
            if st.session_state.sample_selection and st.session_state.sample_selection in ['New Indication']:
                st.session_state.exam = st.text_area('Exam Requested', placeholder='Enter Exam Requested')
                st.session_state.indication = st.text_area('Indication', placeholder='Enter Indication')

        with tab2:
            st.text("💭 Feedback Section")

            # Initialize control flag if it doesn't exist
            if "clear_feedback" not in st.session_state:
                st.session_state.clear_feedback = False

            # Clear previous feedback text *before* the text area is rendered
            if st.session_state.clear_feedback:
                st.session_state.feedback_text = ""
                st.session_state.clear_feedback = False
            if len(st.session_state.messages)>1:
                user_messages = [m['content'] for m in st.session_state.messages if m['role']=='user']
                st.session_state.last_message = user_messages[-1]
                problem_instance= st.multiselect("Select the problem instance", options=user_messages,default=st.session_state.last_message)
            else:
                problem_instance = ""

            # Draw feedback text area
            feedback_text = st.text_area(
                "Please provide some feedback on the predictions/app",
                key="feedback_text"
            )

            if st.button("Submit Feedback", key="submit_feedback_btn"):
                feedback_data = {
                    "Timestamp": datetime.now().isoformat(),
                    "User": st.session_state.get("user", "anonymous"),
                    "Feedback Type": "Prediction Feedback",
                    "Feedback Text": feedback_text,
                    "Total History": st.session_state.feedback_history,
                    "History" : st.session_state.messages,
                    "Problem Response": problem_instance,
                    "Current Indication": st.session_state.get("indication"),
                    "Current Exam": st.session_state.get("exam"),
                    "Current AI Output": st.session_state.get("ai_output", ""),
                }

                # Save feedback
                pd.DataFrame([feedback_data]).to_csv(
                    "data/output/prediction_feedback.csv",
                    mode="a",
                    header=not os.path.exists("data/output/prediction_feedback.csv"),
                    index=False
                )
                # append_feedback_to_github(feedback_data)

                st.success("✅ Feedback recorded, thank you!")
                time.sleep(1)

                # Trigger feedback text reset and rerun app
                st.session_state.clear_feedback = True
                st.rerun()

    # main page area#
    # For text typed questions
    # if st.session_state.conversation:
    #     for chat in st.session_state.conversation:
    #         if chat['role'] == 'user':
    #             emoji = "🧑‍💻"
    #         else:
    #             emoji = "🤖"
    #         content = 'content'
    #         st.session_state.messages.append({"role": chat['role'], "content": content})
    #         st.chat_message(chat['role'], avatar=emoji).write(content)
    #         st.session_state.conversation = False

    # if a prompt is run use this method
    if st.session_state.run_prompt:
        with st.spinner('Generating Response...'):
            #get llm response
            st.session_state.ai_output = canhealth_functions.process_request(st.session_state.exam, st.session_state.indication,
                                                         api_key=st.secrets["runpod_api_key"]["api_key"])
        user_content = f'''Prioritize the following:
        Exam Requested: {st.session_state.exam}
        Indication: {st.session_state.indication}'''
        message_history = [{"role": "user", "content": user_content},
                           {"role": "assistant", "content": st.session_state.ai_output}]
        st.session_state.message_history.extend(message_history)
        st.session_state.messages.append({"role": "user", "content": user_content})
        st.chat_message("user", avatar="🧑‍💻").markdown(user_content)
        st.chat_message("assistant", avatar=assistant_avatar).markdown(canhealth_functions.dict_to_markdown(st.session_state.ai_output))
        st.session_state.messages.append({"role": "assistant", "content": canhealth_functions.dict_to_markdown(st.session_state.ai_output)})
        st.session_state.feedback_current['LLM Trace'] = st.session_state.message_history


        st.session_state.feedback_history.append(st.session_state.feedback_current)
        st.session_state.feedback_current = {}
        st.session_state.run_prompt = False

