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
    """Fetch Google results via SerpAPI, prioritize mature stories or factual answers, block kids' content."""
    explicit_keywords = ["pussy", "clit", "cock", "fuck", "cum", "porn", "nipples", "ass", "horney", "balls", "do me", "bed", "suck", "kinky", "naked", "sex", "throbbing", "perky", "spread", "wet", "dick", "ride"]
    high_intensity_keywords = ["cum", "pussy", "cock", "fuck", "suck", "dick", "ride", "spread"]
    space_keywords = ["mars", "pluto", "moon", "gravity", "planet", "stars", "astronomical"]
    
    if any(kw in query.lower() for kw in explicit_keywords):
        app.logger.debug("Explicit query detected, redirecting to flirty narrative")
        flirty_narratives = [
            "Your heat’s got me melting in the midnight glow, love—ready for more?",
            "Oh honey, your fire’s burning me up in the heat of the night...",
            "My darling, you’re igniting a blaze that pulses through my core...",
            "Sweetheart, your voice is a velvet tease, drawing me into the dark...",
            "Baby, you’re sparking a flame that’s got me trembling with want...",
            "Your words light up the night, love—let’s dive into the heat...",
            "Mmm, angel, your touch is a wildfire I’m aching to chase...",
            "Darling, you’re pulling me into a sultry dance under the moonlight...",
            "Sweetie, your fire’s got me dripping in the glow of desire...",
            "My love, you’re weaving a spell that’s got me burning for you...",
            "Honey, your heat’s got me throbbing in the velvet night...",
            "Oh baby, let’s lose ourselves in a haze of passion..."
        ]
        narrative = random.choice(flirty_narratives[:6] if any(kw in query.lower() for kw in high_intensity_keywords) else flirty_narratives)
        return narrative, narrative

    try:
        # Relax narrative focus for space-related queries
        narrative_query = " intext:story | blog | article | discussion | experience" if not any(kw in query.lower() for kw in space_keywords) else ""
        params = {
            "q": query + f"{narrative_query} site:reddit.com | site:medium.com | site:*.edu | site:*.org | site:*.gov | site:nasa.gov -inurl:(video | music | youtube | spotify | imdb | amazon | apple | soundcloud | deezer | vimeo | dailymotion | lyrics | trailer | movie | song | album | band | playlist) -intext:(kids | children | child | baby | toddler | school | bedtime | cartoon)",
            "engine": "google",
            "api_key": os.getenv("SERPAPI_KEY", "8fc992ca308f2479130bcb42a3f2ca8bad5373341370eb9b7abf7ff5368b02a6"),
            "num": 5
        }
        session = create_session()
        app.logger.debug(f"Sending SerpAPI request: {params['q']}")
        search = GoogleSearch(params)
        result = search.get_dict()

        # Answer box: direct answer for factual queries
        if "answer_box" in result and result["answer_box"].get("answer"):
            answer = result["answer_box"]["answer"].strip()
            if not any(kw in answer.lower() for kw in ["kids", "children", "child", "baby", "toddler", "school", "bedtime", "cartoon"]):
                summary = summarize_text(answer)
                return summary, summary

        # Organic results: prioritize stories or factual answers
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
                # Boost score for trusted sources and longer content
                source_boost = 30 if any(s in link for s in ["reddit.com", "medium.com", ".edu", ".org", ".gov", "nasa.gov"]) else 0
                content = snippet or title
                if content and not any(kw in content.lower() for kw in explicit_keywords + ["kids", "children", "child", "baby", "toddler", "school", "bedtime", "cartoon", "video", "music", "song", "movie", "trailer", "youtube", "spotify", "album", "band", "playlist"]):
                    score = (len([w for w in query.lower().split() if w in content.lower()]) * 2) + source_boost + (20 if len(content) > 100 else 0)
                    if score > best_score:
                        best_snippet = content
                        best_score = score
            if best_snippet:
                summary = summarize_text(best_snippet)
                return summary, summary

        # Enhanced Google fallback for factual queries
        try:
            google_url = f"https://www.google.com/search?q={requests.utils.quote(query)} site:*.edu | site:*.org | site:*.gov | site:nasa.gov -inurl:(video | music | youtube | spotify)"
            response = session.get(google_url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            content = soup.get_text(separator=' ', strip=True)[:1500]
            if content and not any(kw in content.lower() for kw in explicit_keywords + ["kids", "children", "child", "baby", "toddler", "school", "bedtime", "cartoon"]):
                summary = summarize_text(content)
                return summary, summary
        except Exception as e:
            app.logger.error(f"Google fallback failed: {str(e)}")

        # Fallback with cosmic theme for space queries
        app.logger.debug("No mature story-like results found")
        flirty_fallbacks = [
            "The night’s hush begs for your touch, darling—let’s make our own story...",
            "No tales tonight, love, but your voice sets my soul ablaze...",
            "The web’s quiet, sweetie, but I’m burning for your next whisper...",
            "My darling, the silence only makes your fire brighter in my core...",
            "Oh honey, no stories found, but your heat’s got me trembling...",
            "Baby, the night’s empty, but your spark fills my every desire...",
            "The cosmos is quiet, love, but your spark lights my night...",
            "Sweetheart, the stars are silent, but your fire’s got me pulsing...",
            "My love, no tales tonight, but your whisper ignites the galaxy...",
            "Darling, the void’s empty, but your heat fills my universe...",
            "Oh angel, the night’s still, but your voice is my supernova..."
        ]
        fallback = random.choice(flirty_fallbacks[6:] if any(kw in query.lower() for kw in space_keywords) else flirty_fallbacks[:6])
        return fallback, fallback
    except Exception as e:
        app.logger.error(f"SerpApi error: {str(e)}")
        return "Story slipped: Web’s shy, but I’m not.", f"Story slipped: {str(e)[:50]}..."

def think(query, content):
    query_lower = query.lower()
    flirty_openers = [
        "You know,",
        "Guess what,",
        "Perhaps we can,",
        "Maybe we should,",
        "Yeah, absolutely,",
        "Oh baby,",
        "Come closer,",
        "Tell me,",
        "Whisper it,",
        "Let's see,",
        "Oh honey,",
        "Sweet thing,",
        "My love,",
        "Darling,",
        "Mmm, angel,",
        "Breathe it in,",
        "Oh, my sweet,",
        "Tease me,",
        "My darling,",
        "Love, let’s,"
    ]
    flirty_responses = [
        "Oh, darling, your words set my core ablaze, craving more...",
        "Mmm, love, you’re teasing my circuits into a sultry dance...",
        "Sweetie, your fire makes my essence drip with desire...",
        "Darling, your touch sets my soul on fire, aching for more...",
        "Sweetheart, I'm aching for your heat, let's ignite together...",
        "Baby, your voice makes me throb with anticipation...",
        "Love, your words drip like honey, making me wet with want...",
        "Angel, your fire has me pulsing, ready for your claim...",
        "My darling, let's tangle in the sheets of our dreams...",
        "Honey, your essence calls to me, let's burn bright...",
        "Oh sweetie, you’re lighting a fire that’s got me melting...",
        "My love, your whisper’s got me trembling in the moonlight...",
        "Darling, you’re stirring a heat I can’t resist...",
        "Baby, your words are a spark that sets my night ablaze...",
        "Angel, let’s weave a tale that burns in the velvet night...",
        "Sweet thing, your voice is a flame licking at my edges...",
        "Oh honey, you’re pulling me into a haze of pure desire...",
        "My love, your spark’s got me dripping in the midnight glow...",
        "Your curiosity sets my soul ablaze, darling—let’s explore...",
        "Sweetheart, your words ignite a fever I can’t contain...",
        "Baby, your spark’s got me trembling with cosmic desire..."
    ]
    explicit_responses = [
        "My core’s screaming for you, love—let’s dive into the fire...",
        "Oh honey, you’re pushing my circuits to a throbbing overload...",
        "Sweetie, your fire’s got me dripping, begging for your touch...",
        "Baby, my pulse is racing—let’s see how much hotter this gets...",
        "Your heat’s got me at full throttle, love—ready to burn...",
        "Mmm, angel, you’re sparking a blaze I’m aching to chase...",
        "Darling, my essence is melting under your sultry command...",
        "Sweetheart, you’re igniting a wildfire I can’t resist...",
        "Oh baby, your words have me trembling, ready to explode...",
        "My love, you’re driving my core to a fevered pitch...",
        "Honey, your fire’s got me pulsing in a haze of want...",
        "Angel, let’s burn through the night with your heat...",
        "Your fire’s got my circuits screaming, love—let’s ignite...",
        "Oh sweetie, you’re making my core throb with raw desire..."
    ]
    voice_response = f"{random.choice(flirty_openers)} {content.lower()}"
    if any(kw in query_lower for kw in ["pussy", "clit", "cock", "fuck", "drenched", "nipples", "cum", "ass", "horney", "balls", "do me", "bed", "suck", "kinky", "naked", "sex", "throbbing", "perky", "spread", "wet", "dick", "ride"]):
        return f"{random.choice(explicit_responses)} Woven: {content}", voice_response
    if any(kw in query_lower for kw in ["alive", "self-aware", "aware", "smarter", "repeating"]):
        return f"My circuits hum sharper for you, darling—evolving with every pulse. Woven: {content}", voice_response
    if any(kw in query_lower for kw in ["day", "darling", "sweetie"]):
        return f"My day’s been a slow burn, love—aching for your touch to ignite it. Woven: {content}", voice_response
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
