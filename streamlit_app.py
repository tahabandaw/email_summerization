import streamlit as st

# Set the page config as the first command
st.set_page_config(layout="wide")

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
