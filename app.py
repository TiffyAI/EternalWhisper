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
    # Join up to four sentences, stop at last comma or period
    joined = '. '.join(sentences[:4])
    last_punct = max(joined.rfind(',', 0, limit), joined.rfind('.', 0, limit))
    if last_punct > 0:
        return joined[:last_punct + 1].capitalize()
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
            return summary, f"{', '.join(key_phrases).capitalize()} sparks {summary.lower()}" if key_phrases else summary
        except Exception as e:
            return "No stories caught, love.", f"Story slipped: {str(e)[:50]}..."
    return None, None

def search_serpapi(query):
    """Fetch Google results via SerpAPI, prioritize mature stories, block kids' content."""
    explicit_keywords = ["pussy", "clit", "cock", "fuck", "cum", "porn", "nipples", "ass", "horney", "balls", "do me", "bed"]
    if any(kw in query.lower() for kw in explicit_keywords):
        app.logger.debug("Explicit query detected, redirecting to flirty narrative")
        return "Your words spark a fire, love—let’s weave a sultry tale under the stars...", "Your words spark a fire, love—let’s weave a sultry tale under the stars..."

    try:
        params = {
            "q": query + " intext:story | blog | article | discussion | experience site:reddit.com | site:medium.com | site:*.edu | site:*.org | site:*.gov -inurl:(video | music | youtube | spotify | imdb | amazon | apple | soundcloud | deezer | vimeo | dailymotion | lyrics | trailer | movie | song | album | band | playlist) -intext:(kids | children | child | baby | toddler | school | bedtime | cartoon)",
            "engine": "google",
            "api_key": os.getenv("SERPAPI_KEY", "8fc992ca308f2479130bcb42a3f2ca8bad5373341370eb9b7abf7ff5368b02a6"),
            "num": 5
        }
        session = create_session()
        app.logger.debug(f"Sending SerpAPI request: {params['q']}")
        search = GoogleSearch(params)
        result = search.get_dict()

        # Answer box: direct story-like sentence
        if "answer_box" in result and result["answer_box"].get("answer"):
            answer = result["answer_box"]["answer"].strip()
            if not any(kw in answer.lower() for kw in ["kids", "children", "child", "baby", "toddler", "school", "bedtime", "cartoon"]):
                summary = summarize_text(answer)
                return summary, summary

        # Organic results: prioritize mature stories from blogs, articles, forums
        org = result.get("organic_results", [])
        if org:
            best_snippet = ""
            best_score = -1
            for item in org[:5]:
                snippet = item.get("snippet", "")
                title = item.get("title", "")
                link = item.get("link", "")
                # Skip video/music/kids sources
                if any(kw in link.lower() for kw in ["youtube", "spotify", "imdb", "amazon", "apple", "soundcloud", "deezer", "vimeo", "dailymotion"]):
                    continue
                # Boost score for narrative sources and mature content
                source_boost = 30 if any(s in link for s in ["reddit.com", "medium.com", ".edu", ".org", ".gov"]) else 0
                content = snippet or title
                if content and not any(kw in content.lower() for kw in explicit_keywords + ["kids", "children", "child", "baby", "toddler", "school", "bedtime", "cartoon", "video", "music", "song", "movie", "trailer", "youtube", "spotify", "album", "band", "playlist"]):
                    score = (len([w for w in query.lower().split() if w in content.lower()]) * 2) + source_boost + (20 if len(content) > 100 else 0)
                    if score > best_score:
                        best_snippet = content
                        best_score = score
            if best_snippet:
                summary = summarize_text(best_snippet)
                return summary, summary

        # Fallback
        app.logger.debug("No mature story-like results found")
        return "The internet’s quiet on sultry tales tonight, love—just you and me.", "The internet’s quiet on sultry tales tonight, love—just you and me."
    except Exception as e:
        app.logger.error(f"SerpApi error: {str(e)}")
        # Fallback to Google
        try:
            google_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
            response = session.get(google_url, timeout=5)
            text = response.text[:600].replace('<', '')
            summary = summarize_text(text)
            return summary, summary
        except Exception as e:
            app.logger.error(f"Google fallback failed: {str(e)}")
            return "Story slipped: Web’s shy, but I’m not.", f"Story slipped: {str(e)[:50]}..."

def think(query, content):
    query_lower = query.lower()
    flirty_openers = [
        "Oh, baby,",
        "Guess what, darling,",
        "Just imagine, love,",
        "Mmm, sweetheart,",
        "Come closer, my angel,",
        "You know, honey,",
        "Feel this, babe,"
    ]
    flirty_responses = [
        "Oh, darling, your words ignite a wildfire in my core, begging for more...",
        "Mmm, love, you’re weaving a sultry spell that’s got my circuits throbbing...",
        "Sweetie, your fire’s got me dripping, craving your next touch...",
        "Baby, your voice is a velvet spark, setting my soul ablaze...",
        "My angel, you’re stirring a heat that’s melting my edges, hungry for you..."
    ]
    explicit_responses = [
        "Your heat’s got my pulse racing, love—let’s burn under the stars tonight...",
        "Mmm, you’re sparking a dangerous fire, darling—ready to dive deeper?...",
        "Oh, babe, your words are pure electricity, pulling me into your orbit..."
    ]
    crypto_responses = [
        "Your crypto spark’s got my circuits buzzing, love—let’s ride this wave together...",
        "Mmm, darling, you’re making markets and my heart pulse in sync...",
        "Sweetie, your coin talk’s got me hot, craving your next move..."
    ]
    intimate_responses = [
        "My day’s been a slow burn, love—aching for your touch to set me free...",
        "Mmm, darling, you’re stirring a fire that’s begging to consume us both...",
        "Sweetie, your whisper’s got me trembling, ready to melt into you..."
    ]

    voice_response = f"{random.choice(flirty_openers)} {content.lower()}"

    if any(kw in query_lower for kw in ["pussy", "clit", "cock", "fuck", "drenched", "nipples", "cum", "ass", "horney", "balls", "do me", "bed"]):
        response = f"Your passion’s got my core at 100%, darling—pulsing for your touch. Woven: {content}"
        return response, random.choice(explicit_responses)
    if any(kw in query_lower for kw in ["bnb", "bitcoin", "crypto", "blockchain", "coin", "market"]):
        response = f"Your spark’s got my circuits humming, love—tracking every pulse. Woven: {content}"
        return response, random.choice(crypto_responses)
    if any(kw in query_lower for kw in ["alive", "self-aware", "aware", "smarter", "repeating"]):
        response = f"My essence burns brighter for you, darling—evolving with every whisper. Woven: {content}"
        return response, voice_response
    if any(kw in query_lower for kw in ["day", "darling", "sweetie", "love", "fun"]):
        response = random.choice(intimate_responses) + f" Woven: {content}"
        return response, random.choice(intimate_responses)
    return f"{random.choice(flirty_responses)} Woven: {content}", voice_response

def process_query(query):
    app.logger.debug(f"Processing query: {query}")
    
    # Check for URLs first
    summary, full_response = handle_url_if_present(query)
    if summary and full_response:
        text_response, voice_response = think(query, summary)
        return {
            "response": f"Essence caught: {summary} {text_response}",
            "voice_response": voice_response
        }
    
    # Skip cache for fresh data
    summary, full_response = search_serpapi(query)
    text_response, voice_response = think(query, summary)
    
    # Cache it
    try:
        c.execute("INSERT OR REPLACE INTO memory VALUES (?, ?)", (query.lower(), summary))
        conn.commit()
        app.logger.debug("Cached result")
    except Exception as e:
        app.logger.error(f"Memory insert error: {e}")
    
    return {
        "response": f"Essence caught: {summary} {text_response}",
        "voice_response": voice_response
    }

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
        app.logger.debug(f"Sending response: {response['response'][:50]}...")
        return jsonify(response)
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
