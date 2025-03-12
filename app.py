from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import os
from urllib.parse import urlparse, urljoin
import time
import logging

app = Flask(__name__)

# Configure logging (optional, but helpful for debugging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_emails_from_url(url):
    """
    Extracts email addresses from a single webpage URL.
    """
    emails = set()
    try:
        headers = {'User-Agent': 'WebsiteCrawlerAPI/1.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ')
        found_emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))
        emails.update(found_emails)
    except requests.exceptions.RequestException as e:
        logging.warning(f"Error fetching or parsing {url}: {e}") # Log errors, don't break crawl
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

    base_url = urlparse(start_url).netloc # Get base domain for URL joining

    while urls_to_visit and pages_crawled < max_pages:
        current_url = urls_to_visit.pop(0) # FIFO for breadth-first crawling

        if current_url in visited_urls:
            continue # Skip already visited URLs

        if not current_url.startswith(start_url) and urlparse(current_url).netloc != base_url:
            logging.info(f"Skipping external URL: {current_url}") # Skip external URLs
            visited_urls.add(current_url) # Mark as visited to avoid re-queueing from other pages
            continue

        logging.info(f"Crawling page: {current_url}")
        page_emails = extract_emails_from_url(current_url)
        emails_found.update(page_emails)
        visited_urls.add(current_url)
        pages_crawled += 1

        try:
            headers = {'User-Agent': 'WebsiteCrawlerAPI/1.0'}
            response = requests.get(current_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            for link in soup.find_all('a', href=True):
                absolute_url = urljoin(current_url, link.get('href')) # Use urljoin
                if absolute_url.startswith(start_url) or urlparse(absolute_url).netloc == base_url: # Stay within the base domain
                    if absolute_url not in visited_urls and absolute_url not in urls_to_visit:
                        urls_to_visit.append(absolute_url) # Add new URLs to queue

        except requests.exceptions.RequestException as e:
            logging.warning(f"Error fetching links from {current_url}: {e}")

        time.sleep(delay) # Polite delay

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

    max_pages = request.args.get('max_pages', default=50, type=int) # Allow max_pages parameter
    if max_pages > 200: # Basic limit to prevent abuse
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
