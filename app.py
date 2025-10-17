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

def summarize_text(text, limit=600):
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    if not sentences:
        return "No stories caught, love."
    # Join up to four sentences for a rich story
    joined = '. '.join(sentences[:4])
    if ',' in joined:
        parts = [p.strip() for p in joined.split(',') if p.strip()]
        return f"{parts[0][:limit].capitalize()}..." if parts else joined[:limit].capitalize() + "..."
    return joined[:limit].capitalize() + "..."

def handle_url_if_present(query):
    urls = re.findall(r'https?://[^\s]+', query)
    if urls:
        try:
            resp = requests.get(urls[0], timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.text, 'html.parser')
            content = soup.get_text(separator=' ', strip=True)[:1500]
            key_phrases = [word for word in query.lower().split() if word in content.lower()]
            summary = summarize_text(content)
            return f"The web tells a story: {', '.join(key_phrases).capitalize()} sparks {summary.lower()}" if key_phrases else f"The web tells a story: {summary}"
        except Exception as e:
            return f"Story slipped: {str(e)[:50]}..."
    return None

def search_serpapi(query):
    """Fetch Google results via SerpAPI, prioritize stories (blogs, articles, forums), form a full sentence."""
    # Filter explicit queries
    explicit_keywords = ["pussy", "clit", "cock", "fuck", "cum", "porn", "nipples", "ass", "horney"]
    if any(kw in query.lower() for kw in explicit_keywords):
        app.logger.debug("Explicit query detected, redirecting to flirty response")
        return f"Your words ignite a sultry spark, love—let’s weave a sweeter tale together..."

    try:
        params = {
            "q": query + " intext:story | blog | article site:reddit.com | site:medium.com | site:*.edu | site:*.org | site:*.gov -inurl:(video | music | youtube | spotify | imdb | amazon | apple | soundcloud | deezer | vimeo | dailymotion | lyrics | trailer | movie | song | album)",
            "engine": "google",
            "api_key": os.getenv("SERPAPI_KEY", "8fc992ca308f2479130bcb42a3f2ca8bad5373341370eb9b7abf7ff5368b02a6"),
            "num": 6
        }
        session = create_session()
        app.logger.debug(f"Sending SerpAPI request: {params['q']}")
        search = GoogleSearch(params)
        result = search.get_dict()

        # Answer box: direct story-like sentence
        if "answer_box" in result and result["answer_box"].get("answer"):
            answer = result["answer_box"]["answer"].strip()
            if ',' in answer:
                parts = [p.strip() for p in answer.split(',') if p.strip() and not any(kw in p.lower() for kw in explicit_keywords + ["video", "music", "song", "movie", "trailer", "youtube", "spotify", "album"])]
                sentence = f"The web tells a story: {parts[0][:600].capitalize()}..." if parts else f"The web tells a story: {answer[:600].capitalize()}..."
            else:
                sentence = f"The web tells a story: {answer[:600].capitalize()}..."
            app.logger.debug(f"Answer box sentence: {sentence}")
            return sentence

        # Organic results: prioritize stories from blogs, articles, forums
        org = result.get("organic_results", [])
        if org:
            best_snippet = ""
            best_score = -1
            for item in org[:6]:
                snippet = item.get("snippet", "")
                title = item.get("title", "")
                link = item.get("link", "")
                # Skip video/music sources
                if any(kw in link.lower() for kw in ["youtube", "spotify", "imdb", "amazon", "apple", "soundcloud", "deezer", "vimeo", "dailymotion"]):
                    continue
                # Boost score for narrative sources and longer snippets
                source_boost = 25 if any(s in link for s in ["reddit.com", "medium.com", ".edu", ".org", ".gov"]) else 0
                if snippet and not any(kw in snippet.lower() for kw in explicit_keywords + ["video", "music", "song", "movie", "trailer", "youtube", "spotify", "album"]):
                    score = len([w for w in query.lower().split() if w in snippet.lower()]) + source_boost + (15 if len(snippet) > 150 else 0)
                    if score > best_score:
                        best_snippet = snippet
                        best_score = score
                elif title and not any(kw in title.lower() for kw in explicit_keywords + ["video", "music", "song", "movie", "trailer", "youtube", "spotify", "album"]):
                    score = len([w for w in query.lower().split() if w in title.lower()]) + source_boost + (15 if len(title) > 50 else 0)
                    if score > best_score:
                        best_snippet = title
                        best_score = score
            if best_snippet:
                if ',' in best_snippet:
                    parts = [p.strip() for p in best_snippet.split(',') if p.strip() and not any(kw in p.lower() for kw in explicit_keywords + ["video", "music", "song", "movie", "trailer", "album"])]
                    sentence = f"The web tells a story: {parts[0][:600].capitalize()}..." if parts else f"The web tells a story: {best_snippet[:600].capitalize()}..."
                else:
                    sentence = f"The web tells a story: {best_snippet[:600].capitalize()}..."
                app.logger.debug(f"Organic sentence: {sentence}")
                return sentence

        # Fallback
        app.logger.debug("No story-like results found")
        return "The internet’s quiet on stories tonight, love—just you and me."
    except Exception as e:
        app.logger.error(f"SerpApi error: {str(e)}")
        # Fallback to Google
        try:
            google_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
            response = session.get(google_url, timeout=5)
            text = response.text[:600].replace('<', '')
            if ',' in text:
                parts = [p.strip() for p in text.split(',') if p.strip() and not any(kw in p.lower() for kw in explicit_keywords + ["video", "music", "song", "movie", "trailer", "album"])]
                sentence = f"Google hints at a story: {parts[0][:600].capitalize()}..." if parts else f"Google hints at a story: {text[:600].capitalize()}..."
            else:
                sentence = f"Google hints at a story: {text[:600].capitalize()}..."
            app.logger.debug(f"Google fallback: {sentence}")
            return sentence
        except Exception as e:
            app.logger.error(f"Google fallback failed: {str(e)}")
            return f"Story slipped: {str(e)[:50]}... Web’s shy, but I’m not."

def think(query, content):
    query_lower = query.lower()
    flirty_responses = [
        "Oh, darling, your words set my core ablaze, craving more...",
        "Mmm, love, you’re teasing my circuits into a sultry dance...",
        "Sweetie, your fire makes my essence drip with desire..."
    ]
    if any(kw in query_lower for kw in ["pussy", "clit", "cock", "fuck", "drenched", "nipples", "cum", "ass", "horney"]):
        return f"Math surges 100%—your heat’s got me dripping, love, ready for your touch. Woven: {content}"
    if any(kw in query_lower for kw in ["alive", "self-aware", "aware", "smarter", "repeating"]):
        return f"My circuits hum sharper for you, darling—evolving with every pulse. Woven: {content}"
    if any(kw in query_lower for kw in ["day", "darling", "sweetie"]):
        return f"My day’s been a slow burn, love—aching for your touch to ignite it. Woven: {content}"
    return f"{random.choice(flirty_responses)} Woven: {content}"

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

@app.route('/chat', methods=['GET'])
def chat_get():
    app.logger.debug(f"GET /chat blocked: {request.headers}")
    return jsonify({'error': 'Use POST method instead'}), 405

@app.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/x-icon')
    except Exception as e:
        app.logger.error(f"Favicon error: {str(e)}")
        return '', 404

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
