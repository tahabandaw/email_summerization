import re
import logging
import streamlit as st
from email import message_from_bytes
from transformers import pipeline
import imapclient
import sys
import torch
import os
# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')

# Disable TensorFlow optimizations and GPU features
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

# Initialize summarizer with a lightweight model
summarizer = pipeline('summarization', model='sshleifer/distilbart-cnn-12-6', from_pt=True, framework='pt')

def is_valid_email(email):
    """Basic validation for email format."""
    regex = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
    return re.match(regex, email)

def fetch_emails(email, password, folder='INBOX', limit=10):
    try:
        imap = imapclient.IMAPClient('imap.gmail.com', ssl=True)
        imap.login(email, password)
        imap.select_folder(folder, readonly=True)
        uids = imap.search(['ALL'])[-limit:]
        messages = imap.fetch(uids, ['BODY[]'])
        emails = []
        for uid, data in messages.items():
            msg = message_from_bytes(data[b'BODY[]'])
            if msg.is_multipart():
                content = ''
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        payload = part.get_payload(decode=True)
                        if payload:
                            content = payload.decode('utf-8', 'ignore')
                            break
                if not content:
                    content = 'No text content found'
            else:
                content = msg.get_payload(decode=True).decode('utf-8', 'ignore') if msg.get_payload(decode=True) else 'No content found'
            emails.append({
                'id': uid,
                'subject': msg.get('Subject', 'No Subject'),
                'from': msg.get('From', 'Unknown'),
                'content': content,
                'date': msg.get('Date', 'Unknown'),
            })
        imap.logout()
        return emails
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")
        return []

def categorize_email(subject):
    subject_lower = subject.lower()
    if any(keyword in subject_lower for keyword in ['invoice', 'payment', 'bill']):
        return 'Finance'
    elif any(keyword in subject_lower for keyword in ['meeting', 'schedule', 'project']):
        return 'Work'
    elif any(keyword in subject_lower for keyword in ['offer', 'discount', 'promotion']):
        return 'Promotions'
    else:
        return 'Others'

def summarize_text(text):
    try:
        if len(text.split()) < 10:
            return text  # return the text as is if it's too short
        max_len = min(130, len(text.split()) * 2)
        summary = summarizer(text, max_length=max_len, min_length=30, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        logging.error(f"Error summarizing text: {e}")
        return "Unable to generate summary."

def main():
    st.set_page_config(layout="wide")
    st.title('\U0001F4E8 Email Dashboard')

    # Sidebar for email and password input with fetch button
    email = st.sidebar.text_input('\U0001F4E8 Email')
    password = st.sidebar.text_input('\U0001F511 Password', type='password')
    fetch_emails_button = st.sidebar.button('\U0001F4E5 Fetch Emails')

    # Load emails in session state at the start
    if 'emails' not in st.session_state:
        st.session_state.emails = []

    if fetch_emails_button:
        if email and password:
            with st.spinner('Fetching emails...'):
                try:
                    fetched_emails = fetch_emails(email, password)
                    if fetched_emails:
                        for email in fetched_emails:
                            email['category'] = categorize_email(email['subject'])
                            email['summary'] = summarize_text(email['content'])
                        st.session_state.emails = fetched_emails
                    else:
                        st.error('No emails fetched. Please check your credentials or try again later.')
                except Exception as e:
                    st.error(f"An error occurred while fetching emails: {e}")
        else:
            st.warning('Please enter your email and password to fetch emails.')

    if st.session_state.emails:
        # Email categories
        categories = ['All', 'Finance', 'Work', 'Promotions', 'Others']
        selected_category = st.radio("Filter Emails", categories, horizontal=True)

        filtered_emails = st.session_state.emails if selected_category == 'All' else [
            email for email in st.session_state.emails if email.get('category', 'Others') == selected_category]

        for email in filtered_emails:
            with st.container():
                # Display email summary with a button to show full content
                with st.expander(f"\U0001F4E7 Subject: {email['subject']}", expanded=False):
                    st.markdown(f"""
                    - **From:** {email['from']}
                    - **Date:** {email['date']}
                    - **Category:** {email['category']}
                    - **Summary:** {email['summary']}
                    """, unsafe_allow_html=True)

                    # Display full email content inside the expander
                    st.text_area("Full Email Content", email['content'], height=300, disabled=True)

                st.divider()  # For better visual separation
    else:
        st.write("No emails to display.")

if __name__ == '__main__':
    main()
