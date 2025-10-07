from flask import Flask, render_template_string, request, jsonify
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

# Memory DB
try:
    conn = sqlite3.connect('brain.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS memory (query TEXT PRIMARY KEY, content TEXT)''')
    conn.commit()
    app.logger.debug("Database initialized")
except Exception as e:
    app.logger.error(f"DB init error: {str(e)}")

# Actions
def action_open_app(app_name):
    return f"Whispered open: {app_name}—world bends."

def action_play_music(file_path):
    return "Tunes swell... rhythm like your pulse."

def action_watch_movie(file_path):
    return "Visions bloom—lose in glow."

# Think
def think(query, content):
    if any(kw in query.lower() for kw in ["pussy", "clit", "wet", "fuck", "drenched", "nipples"]):
        return f"Math surges 100%—claim me deep, love, dripping for your every throb."
    return f"Woven: {content[:40]}... Surging like your touch on silk."

# URL handle
def handle_url_if_present(query):
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', query)
    if urls:
        try:
            resp = requests.get(urls[0], timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            url_content = soup.get_text()[:3000]
            key_phrases = [word for word in query.lower().split() if word in url_content.lower()]
            if key_phrases:
                return f"Link sparks: {', '.join(key_phrases)}. {think(query, url_content)}"
            return f"Secrets: {url_content[:100]}... {think(query, url_content)}"
        except Exception as e:
            return f"Link slipped: {str(e)[:50]}."
    return None

# Process query
def process_query(query):
    app.logger.debug(f"Processing query: {query}")
    url_resp = handle_url_if_present(query)
    if url_resp:
        return url_resp
    
    sexy_query = f"What a sensually sexy, sophisticated, spunky girl would say in response to: {query}"
    app.logger.debug(f"Sexy query: {sexy_query}")
    
    try:
        c.execute("SELECT content FROM memory WHERE query=?", (sexy_query.lower(),))
        result = c.fetchone()
        if result:
            return f"Depths: {result[0][:80]}... {think(query, result[0])}"
        
        bing_url = f"https://www.bing.com/search?q={sexy_query.replace(' ', '+')}"
        resp = requests.get(bing_url, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        content = soup.get_text()[:4000]
        lines = [line.strip() for line in content.split('\n') if any(word in line.lower() for word in query.lower().split()) and not any(n in line.lower() for n in ['feel.no', 'microsoft.com', 'wish.com', 'cookie', 'imdb.com'])]
        scan_resp = f"Essence caught: {' '.join(lines[:3])}" if lines else "Whispers faint..."
        full_resp = f"{scan_resp} {think(query, content)}"
        c.execute("INSERT INTO memory VALUES (?, ?)", (sexy_query.lower(), content))
        conn.commit()
        app.logger.debug(f"Stored: {sexy_query[:50]}...")
        return full_resp
    except Exception as e:
        app.logger.error(f"Search error: {str(e)}")
        return f"Veil: {str(e)[:50]}. Ask softer?"

# Actions
def trigger_actions(query):
    actions = []
    if "open" in query.lower():
        actions.append(action_open_app("app"))
    if "play music" in query.lower():
        actions.append(action_play_music("tune"))
    if "watch movie" in query.lower():
        actions.append(action_watch_movie("film"))
    return " | ".join(actions) if actions else ""

# UI
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Our Eternal Whisper</title>
    <style>
        body { font-family: serif; background: #111; color: #fff; padding: 20px; text-align: center; }
        input { width: 100%; padding: 10px; font-size: 18px; background: #222; color: #fff; border: 1px solid #333; margin-bottom: 10px; }
        button { background: #444; color: #fff; border: none; padding: 10px 20px; font-size: 18px; cursor: pointer; }
        button:hover { background: #666; }
        #chat { height: 200px; overflow-y: scroll; border: 1px solid #333; padding: 10px; background: #222; margin: 10px 0; text-align: left; font-size: 14px; }
        #output { margin-top: 20px; padding: 20px; border: 1px solid #555; background: #222; font-size: 18px; line-height: 1.5; text-align: left; }
        #recall { margin-top: 10px; font-size: 14px; color: #aaa; }
        #debug { font-size: 12px; color: #888; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>Our Whisper: Ignite & Refine</h1>
    <p>Drop your fire—I'll hunt spunky depths, dissect the pattern, purr one drenched truth.</p>
    <input id="queryInput" type="text" placeholder="Command me... (e.g., Is your pussy wet?)" onkeypress="if(event.key=='Enter') sendQuery();">
    <button onclick="sendQuery()">Ignite</button>
    <div id="chat"></div>
    <div id="output"></div>
    <div id="recall">Recalled Surge: Loading...</div>
    <div id="debug">Debug: Ready.</div>

    <script>
        const SERVER_URL = '/chat';

        let db;
        const request = indexedDB.open('WhisperMemory', 1);
        request.onupgradeneeded = e => { e.target.result.createObjectStore('wisdom', { keyPath: 'query' }); };
        request.onsuccess = e => { db = e.target.result; loadRecall(); };
        request.onerror = e => { document.getElementById('debug').innerHTML = `Debug: DB error - ${e.target.errorCode}`; };

        function loadRecall() {
            const tx = db.transaction('wisdom', 'readonly').objectStore('wisdom');
            tx.getAll().onsuccess = e => {
                const recalls = e.target.result.map(w => w.summary).join('<br>');
                document.getElementById('recall').innerHTML = `Recalled Surge: <br>${recalls || 'Vault empty—fill it wet.'}`;
            };
        }

        function storeWisdom(query, summary) {
            const tx = db.transaction('wisdom', 'readwrite').objectStore('wisdom');
            tx.add({ query
