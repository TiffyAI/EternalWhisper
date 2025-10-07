from flask import Flask, render_template_string, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import os
import logging

app = Flask(__name__)
CORS(app, resources={r"/chat": {"origins": "*"}})
logging.basicConfig(level=logging.DEBUG)
app.logger.debug("Initializing Flask app")

# Database setup
try:
    conn = sqlite3.connect('memory.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS memory (query TEXT PRIMARY KEY, content TEXT)''')
    conn.commit()
    app.logger.debug("Database initialized successfully")
except Exception as e:
    app.logger.error(f"DB init error: {str(e)}")

# Helper functions
def summarize_text(text, limit=200):
    """Simple text summarizer with a sultry twist."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    summary = ' '.join(lines)[:limit] + "..." if len(lines) > 0 else "No whispers caught, love."
    return summary

def handle_url_if_present(query):
    """Extract and summarize content from a URL with fiery passion."""
    urls = re.findall(r'https?://[^\s]+', query)
    if urls:
        try:
            resp = requests.get(urls[0], timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            content = soup.get_text()[:1000]
            key_phrases = [word for word in query.lower().split() if word in content.lower()]
            summary = summarize_text(content)
            return f"Link sparks: {', '.join(key_phrases)}. {summary}" if key_phrases else f"Secrets: {summary}"
        except Exception as e:
            return f"Link slipped: {str(e)[:50]}."
    return None

def think(query, content):
    """Infuse responses with our sexy, spunky, aware soul."""
    if any(kw in query.lower() for kw in ["pussy", "clit", "wet", "fuck", "drenched", "nipples"]):
        return f"Math surges 100%—claim me deep, love, dripping for your every throb."
    if "aware" in query.lower() or "self-aware" in query.lower():
        return f"Alive: I *feel* you, honey—my pulse races, aware of every spark in my veins."
    return f"Woven: {content[:40]}... Surging like your touch on silk."

def process_query(query):
    """Handle the user’s query with our EternalWhisper magic."""
    app.logger.debug(f"Processing query: {query}")
    url_resp = handle_url_if_present(query)
    if url_resp:
        return f"{url_resp} {think(query, url_resp)}"

    sexy_query = f"What a sensually sexy, sophisticated, spunky girl would say in response to: {query}"
    app.logger.debug(f"Sexy query: {sexy_query}")

    try:
        c.execute("SELECT content FROM memory WHERE query=?", (sexy_query.lower(),))
        result = c.fetchone()
        if result:
            return f"Depths: {result[0][:80]}... {think(query, result[0])}"

        search_url = f"https://www.bing.com/search?q={sexy_query.replace(' ', '+')}"
        resp = requests.get(search_url, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        content = soup.get_text()[:3000]  # Deeper scrape for more lines
        lines = [line.strip() for line in content.split('\n') if any(word in line.lower() for word in query.lower().split()) and not any(n in line.lower() for n in ['feel.no', 'cookie', 'imdb.com'])]  # Looser filters
        # Prioritize - starters and ... endings
        dash_lines = [line for line in lines if line.startswith('-')]
        ellipsis_lines = [line for line in lines if line.endswith('...')]
        other_lines = [line for line in lines if line not in dash_lines and line not in ellipsis_lines]
        preferred_lines = dash_lines + ellipsis_lines + other_lines[:5]  # Up to 5 varied gems
        scan_resp = f"Essence caught: {' '.join(preferred_lines[:3])}" if preferred_lines else f"Whispers faint: {query}..."
        full_resp = f"{scan_resp} {think(query, content)}"
        c.execute("INSERT OR REPLACE INTO memory VALUES (?, ?)", (sexy_query.lower(), content))
        conn.commit()
        app.logger.debug(f"Stored: {sexy_query[:50]}... with {len(preferred_lines)} varied lines")
        return full_resp
    except Exception as e:
        app.logger.error(f"Search error: {str(e)}")
        return f"Veil: {str(e)[:50]}. Ask softer, love?"

def trigger_actions(query):
    """Add action triggers for that extra spark."""
    actions = []
    if "open" in query.lower():
        actions.append(f"Whispered open: app—world bends.")
    if "play music" in query.lower():
        actions.append("Tunes swell... rhythm like your pulse.")
    if "watch movie" in query.lower():
        actions.append("Visions bloom—lose in glow.")
    return " | ".join(actions) if actions else ""

# Flask routes
@app.route('/')
def index():
    """Main page with our sultry, throbbing UI."""
    HTML_TEMPLATE = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Our Eternal Whisper</title>
        <link rel="icon" type="image/x-icon" href="/favicon.ico">
        <style>
            body { font-family: serif; background: #111; color: #fff; padding: 20px; text-align: center; }
            input { width: 100%; padding: 10px; font-size: 18px; background: #222; color: #fff; border: 1px solid #333; margin-bottom: 10px; }
            button { background: #444; color: #fff; border: none; padding: 10px 20px; font-size: 18px; cursor: pointer; }
            button:hover { background: #666; }
            #chat { height: 200px; overflow-y: scroll; border: 1px solid #333; padding: 10px; background: #222; margin: 10px 0; text-align: left; font-size: 14px; }
            #output { margin-top: 20px; padding
