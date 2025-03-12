from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)

def extract_emails_from_url(url):
    """
    Scrapes a given URL and extracts email addresses.
    """
    try:
        headers = {'User-Agent': 'EmailScraperAPI/1.0'} # Setting a User-Agent
        response = requests.get(url, headers=headers, timeout=15) # Added timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ') # Extract all text
        emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)) # Basic email regex
        return list(emails)
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {e}"}

@app.route('/extract-emails', methods=['GET'])
def api_extract_emails():
    target_url = request.args.get('url')
    if not target_url:
        return jsonify({"error": "URL parameter is missing."}), 400

    emails = extract_emails_from_url(target_url)
    return jsonify({"url": target_url, "emails": emails})

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Email Scraper API is running. Use /extract-emails?url=<target_url> to extract emails."})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000)) # For Render deployment, use PORT env variable
    app.run(host='0.0.0.0', port=port) # Listen on all interfaces
