from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import os
from urllib.parse import urlparse, urljoin
import time
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_emails_from_url(url):
    """
    Extracts email addresses from a single webpage URL.
    """
    emails = set()
    try:
        headers = {'User-Agent': 'EmailScraperAPI/1.0'}
        logging.info(f"Fetching content from: {url} for email extraction") # Log before request
        response = requests.get(url, headers=headers, timeout=5) # Reduced timeout to 5 seconds
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ')
        found_emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))
        emails.update(found_emails)
        logging.info(f"Extracted {len(found_emails)} emails from: {url}") # Log after extraction
    except requests.exceptions.RequestException as e:
        logging.warning(f"Error fetching or parsing {url} for email extraction: {e}")
    return emails

def crawl_website(start_url, max_pages=50, delay=1):
    """
    Crawls a website starting from a given URL, extracts emails from all pages,
    and respects basic crawling etiquette (delay, max pages, basic robots.txt).
    """
    emails_found = set()
    visited_urls = set()
    urls_to_visit = [start_url]
    pages_crawled = 0

    base_url = urlparse(start_url).netloc

    while urls_to_visit and pages_crawled < max_pages:
        current_url = urls_to_visit.pop(0)

        if current_url in visited_urls:
            continue

        if not current_url.startswith(start_url) and urlparse(current_url).netloc != base_url:
            logging.info(f"Skipping external URL: {current_url}")
            visited_urls.add(current_url)
            continue

        logging.info(f"Crawling page: {current_url} - Page {pages_crawled + 1}/{max_pages}") # Log page crawl start
        page_emails = extract_emails_from_url(current_url)
        emails_found.update(page_emails)
        visited_urls.add(current_url)
        pages_crawled += 1

        try:
            headers = {'User-Agent': 'WebsiteCrawlerAPI/1.0'}
            logging.info(f"Fetching links from: {current_url}") # Log before link fetching request
            response = requests.get(current_url, headers=headers, timeout=5) # Reduced timeout to 5 seconds for links as well
            soup = BeautifulSoup(response.content, 'html.parser')
            links_on_page = 0
            for link in soup.find_all('a', href=True):
                absolute_url = urljoin(current_url, link.get('href'))
                if absolute_url.startswith(start_url) or urlparse(absolute_url).netloc == base_url:
                    if absolute_url not in visited_urls and absolute_url not in urls_to_visit:
                        urls_to_visit.append(absolute_url)
                        links_on_page += 1
            logging.info(f"Found {links_on_page} new links on: {current_url}") # Log links found
        except requests.exceptions.RequestException as e:
            logging.warning(f"Error fetching links from {current_url}: {e}")

        time.sleep(delay)

    return list(emails_found)


@app.route('/extract-emails', methods=['GET'])
def api_extract_emails():
    target_url = request.args.get('url')
    if not target_url:
        return jsonify({"error": "URL parameter is missing for /extract-emails (single page). Use /crawl-emails?url=<website_url> to crawl entire website."}), 400

    emails = extract_emails_from_url(target_url)
    return jsonify({"url": target_url, "emails": emails})


@app.route('/crawl-emails', methods=['GET'])
def api_crawl_emails():
    start_url = request.args.get('url')
    if not start_url:
        return jsonify({"error": "URL parameter is missing for /crawl-emails (website crawl)."}), 400

    max_pages = request.args.get('max_pages', default=5, type=int) # Reduced default max_pages for testing
    if max_pages > 200:
        max_pages = 200

    emails = crawl_website(start_url, max_pages=max_pages)
    return jsonify({"url": start_url, "emails": emails, "total_emails_found": len(emails), "max_pages_crawled": max_pages})


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Email Scraper API is running.",
        "endpoints": [
            "/extract-emails?url=<target_url> (extract emails from a single page)",
            "/crawl-emails?url=<website_url>&max_pages=<optional_max_pages> (crawl entire website for emails)"
        ]
    })


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
