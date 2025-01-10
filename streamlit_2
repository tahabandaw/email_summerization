import streamlit as st
import imapclient
from email import message_from_bytes
from transformers import pipeline
import logging
import os
import json

# Configure logging
logging.basicConfig(filename='app.log', level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')

# Set environment variable to disable oneDNN (for TensorFlow, if using)
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Lazy loading for the summarization model
@st.cache_resource
def load_summarizer():
    return pipeline('summarization', model='facebook/bart-base')

summarizer = load_summarizer()

# File to store emails
EMAILS_JSON_FILE = 'emails.json'

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

def save_emails_to_json(emails, filename=EMAILS_JSON_FILE):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(emails, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving emails to JSON: {e}")

def load_emails_from_json(filename=EMAILS_JSON_FILE):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logging.error(f"Error loading emails from JSON: {e}")
        return []

def categorize_email(subject):
    subject_lower = subject.lower()
    if any(keyword in subject_lower for keyword in ['invoice', 'payment', 'bill']):
        return 'Finance'
    elif any(keyword in subject_lower for keyword in ['meeting', 'schedule', 'project']):
        return 'Work'
    elif any(keyword in subject_lower for keyword in ['offer', 'discount', 'promotion','logical']):
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
       
