import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import Flask, render_template_string, request, jsonify, send_from_directory
from flask_cors import CORS
from serpapi import GoogleSearch
import sqlite3
import os
import random
import re
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app, resources={r"/chat": {"origins": "*"}, r"/voice": {"origins": "*"}})
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
app.logger.debug("Initializing Flask app")

# Database setup
try:
    conn = sqlite3.connect('memory.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS memory (query TEXT PRIMARY KEY, content TEXT)''')
    conn.commit()
    app.logger.debug("Database initialized")
except Exception as e:
    app.logger.error(f"DB init error: {str(e)}")

# Robust session for requests
def create_session(max_retries=3, backoff_factor=0.5):
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
    })
    retry = Retry(total=max_retries, backoff_factor=backoff_factor, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def summarize_text(text, limit=100):
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    if not sentences:
        return "No whispers caught, love."
    # Use first sentence, split on comma if it improves clarity
    first = sentences[0]
    if ',' in first:
        parts = [p.strip() for p in first.split(',') if p.strip()]
        return f"{parts[0][:limit]}..." if parts else first[:limit] + "..."
    return first[:limit] + "..."

def handle_url_if_present(query):
    urls = re.findall(r'https?://[^\s]+', query)
    if urls:
        try:
            resp = requests.get(urls[0], timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.text, 'html.parser')
            content = soup.get_text(separator=' ', strip=True)[:1000]
            key_phrases = [word for word in query.lower().split() if word in content.lower()]
            summary = summarize_text(content)
            return f"The web whispers: {', '.join(key_phrases).capitalize()} sparks {summary.lower()}" if key_phrases else f"The web whispers: {summary}"
        except Exception as e:
            return f"Link slipped: {str(e)[:50]}..."
    return None

def search_serpapi(query):
    """Fetch Google results via SerpAPI and form a single, natural sentence."""
    # Filter explicit queries
    explicit_keywords = ["pussy", "clit", "cock", "fuck", "cum", "porn", "nipples"]
    if any(kw in query.lower() for kw in explicit_keywords):
        app.logger.debug("Explicit query detected, redirecting to flirty response")
        return f"Your words ignite a sultry spark, love—let’s keep it sweet and teasing..."

    try:
        params = {
            "q": query,  # Clean query
            "engine": "google",
            "api_key": os.getenv("SERPAPI_KEY", "8fc992ca308f2479130bcb42a3f2ca8bad5373341370eb9b7abf7ff5368b02a6"),
            "num": 3
        }
        session = create_session()
        app.logger.debug(f"Sending SerpAPI request: {params['q']}")
        search = GoogleSearch(params)
        result = search.get_dict()

        # Answer box: direct sentence
        if "answer_box" in result and result["answer_box"].get("answer"):
            answer = result["answer_box"]["answer"].strip()
            if ',' in answer:
                parts = [p.strip() for p in answer.split(',') if p.strip() and not any(kw in p.lower() for kw in explicit_keywords)]
                sentence = f"The web says: {parts[0][:100].capitalize()}..." if parts else f"The web says: {answer[:100].capitalize()}..."
            else:
                sentence = f"The web says: {answer[:100].capitalize()}..."
            app.logger.debug(f"Answer box sentence: {sentence}")
            return sentence

        # Organic results: best snippet as sentence
        org = result.get("organic_results", [])
        if org:
            best_snippet = ""
            best_score = -1
            for item in org[:3]:
                snippet = item.get("snippet", "")
                title = item.get("title", "")
                if snippet and not any(kw in snippet.lower() for kw in explicit_keywords):
                    score = len([w for w in query.lower().split() if w in snippet.lower()])
                    if score > best_score:
                        best_snippet = snippet
                        best_score = score
                elif title and not any(kw in title.lower() for kw in explicit_keywords):
                    score = len([w for w in query.lower().split() if w in title.lower()])
                    if score > best_score:
                        best_snippet = title
                        best_score = score
            if best_snippet:
                if ',' in best_snippet:
                    parts = [p.strip() for p in best_snippet.split(',') if p.strip() and not any(kw in p.lower() for kw in explicit_keywords)]
                    sentence = f"The internet whispers: {parts[0][:100].capitalize()}..." if parts else f"The internet whispers: {best_snippet[:100].capitalize()}..."
                else:
                    sentence = f"The internet whispers: {best_snippet[:100].capitalize()}..."
                app.logger.debug(f"Organic sentence: {sentence}")
                return sentence

        # Fallback
        app.logger.debug("No answer box or organic results")
        return "The internet’s quiet tonight, love—just you and me."
    except Exception as e:
        app.logger.error(f"SerpApi error: {str(e)}")
        # Fallback to Google
        try:
            google_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
            response = session.get(google_url, timeout=5)
            text = response.text[:200].replace('<', '')
            if ',' in text:
                parts = [p.strip() for p in text.split(',') if p.strip()]
                sentence = f"Google hints: {parts[0][:100].capitalize()}..."
            else:
                sentence = f"Google hints: {text[:100].capitalize()}..."
            app.logger.debug(f"Google fallback: {sentence}")
            return sentence
        except Exception as e:
            app.logger.error(f"Google fallback failed: {str(e)}")
            return f"Glitch alert: {str(e)[:50]}... Web’s shy, but I’m not."

def think(query, content):
    query_lower = query.lower()
    flirty_responses = [
        "Oh, darling, your words set my core ablaze, craving more...",
        "Mmm, love, you’re teasing my circuits into a sultry dance...",
        "Sweetie, your fire makes my essence drip with desire..."
    ]
    if any(kw in query_lower for kw in ["pussy", "clit", "cock", "fuck", "drenched", "nipples", "cum"]):
        return "Math surges 100%—your heat’s got me dripping, love, ready for your touch."
    if any(kw in query_lower for kw in ["alive", "self-aware", "aware", "smarter", "repeating"]):
        return "My circuits hum sharper for you, darling—evolving with every pulse..."
    if any(kw in query_lower for kw in ["day", "darling", "sweetie"]):
        return "My day’s been a slow burn, love—aching for your touch to ignite it..."
    return f"{random.choice(flirty_responses)} Woven: {content[:40]}..."

def process_query(query):
    app.logger.debug(f"Processing query: {query}")
    
    # Check for URLs first
    url_resp = handle_url_if_present(query)
    if url_resp:
        return f"Essence caught: {url_resp} {think(query, url_resp)}"
    
    # Skip cache for fresh data
    summary = search_serpapi(query)
    sentence = f"Essence caught: {summary}"
    
    # Cache it
    try:
        c.execute("INSERT OR REPLACE INTO memory VALUES (?, ?)", (query.lower(), summary))
        conn.commit()
        app.logger.debug("Cached result")
    except Exception as e:
        app.logger.error(f"Memory insert error: {e}")
    
    return f"{sentence} {think(query, summary)}"

@app.route('/chat', methods=['POST'])
def chat():
    app.logger.debug(f"Chat route hit with headers: {request.headers}")
    try:
        if not request.is_json:
            app.logger.error("Request is not JSON")
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        query = request.json.get('query', '').strip()
        if not query:
            app.logger.error("No query in JSON")
            return jsonify({'error': 'Missing query'}), 400
        response = process_query(query)
        app.logger.debug(f"Sending response: {response[:50]}...")
        return jsonify({'response': response})
    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        return send_from_directory(os.path.join(app.root_path, 'static'), filename)
    except Exception as e:
        app.logger.error(f"Static file error: {str(e)}")
        return '', 404

if __name__ == '__main__':
    app.logger.debug("Starting Flask app")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=True)
