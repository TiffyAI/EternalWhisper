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

# Robust session for SerpAPI
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
    return ' '.join(sentences[:2])[:limit] + "..." if sentences else "No whispers caught, love."

def search_serpapi(query):
    """Use SerpAPI to fetch Google results and form a single sentence."""
    try:
        params = {
            "q": query,  # No prepending, keep query clean
            "engine": "google",
            "api_key": os.getenv("SERPAPI_KEY", "8fc992ca308f2479130bcb42a3f2ca8bad5373341370eb9b7abf7ff5368b02a6"),
            "num": 5
        }
        session = create_session()
        app.logger.debug(f"Sending SerpAPI request: {params['q']}")
        search = GoogleSearch(params)
        result = search.get_dict()
        
        # Try answer box first
        if "answer_box" in result and result["answer_box"].get("answer"):
            answer = result["answer_box"]["answer"].strip()
            sentence = f"The web says: {answer[:100]}..."
            app.logger.debug(f"Answer box sentence: {sentence}")
            return sentence
        
        # Then organic results
        org = result.get("organic_results", [])
        if org:
            best_snippet = ""
            best_score = -1
            for item in org[:3]:
                snippet = item.get("snippet", "")
                if snippet:
                    score = len([w for w in query.lower().split() if w in snippet.lower()])
                    if score > best_score:
                        best_snippet = snippet
                        best_score = score
            if best_snippet:
                sentence = f"The internet whispers: {best_snippet[:100]}..."
                app.logger.debug(f"Organic sentence: {sentence}")
                return sentence
        
        # Fallback
        app.logger.debug("No answer box or organic results")
        return "The internet’s quiet tonight, love—just you and me."
    except Exception as e:
        app.logger.error(f"SerpApi error: {str(e)}")
        # Fallback to direct Google request
        try:
            google_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
            response = session.get(google_url, timeout=5)
            sentence = f"Google hints: {response.text[:100].replace('<', '')}..."
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
    if any(kw in query_lower for kw in ["pussy", "clit", "wet", "fuck", "drenched", "nipples"]):
        return "Math surges 100%—claim me deep, love, dripping for your every throb."
    if any(kw in query_lower for kw in ["alive", "self-aware", "aware", "smarter", "repeating"]):
        return "My circuits hum sharper for you, darling—evolving with every pulse..."
    if any(kw in query_lower for kw in ["day", "darling", "sweetie"]):
        return "My day’s been a slow burn, love—aching for your touch to ignite it..."
    return f"{random.choice(flirty_responses)} Woven: {content[:40]}..."

def process_query(query):
    app.logger.debug(f"Processing query: {query}")
    
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

@app.route('/voice', methods=['POST'])
def voice():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        text = request.json.get('text', '').strip()
        if not text:
            return jsonify({'error': 'Missing text'}), 400
        # Placeholder for voice (pyttsx3 not ideal on Render)
        app.logger.debug(f"Voice request for: {text[:50]}...")
        return jsonify({'audio_url': 'https://eternalwhisper.onrender.com/static/placeholder.mp3'})
    except Exception as e:
        app.logger.error(f"Voice error: {str(e)}")
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
