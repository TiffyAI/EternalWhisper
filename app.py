from flask import Flask, render_template_string, request, jsonify, send_from_directory
from flask_cors import CORS
from serpapi import GoogleSearch
import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import os
import logging
import random
import pyttsx3

app = Flask(__name__)
CORS(app, resources={r"/chat": {"origins": "*"}, r"/voice": {"origins": "*"}})
logging.basicConfig(level=logging.DEBUG)
app.logger.debug("Initializing Flask app")

try:
    conn = sqlite3.connect('memory.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS memory')  # Clear cache
    c.execute('''CREATE TABLE IF NOT EXISTS memory (query TEXT PRIMARY KEY, content TEXT)''')
    conn.commit()
    app.logger.debug("Database initialized, cache cleared")
except Exception as e:
    app.logger.error(f"DB init error: {str(e)}")

def summarize_text(text, limit=200):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return ' '.join(lines)[:limit] + "..." if lines else "No whispers caught, love."

def handle_url_if_present(query):
    urls = re.findall(r'https?://[^\s]+', query)
    if urls:
        try:
            resp = requests.get(urls[0], timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.text, 'html.parser')
            content = soup.get_text(separator=' ', strip=True)[:1000]
            key_phrases = [word for word in query.lower().split() if word in content.lower()]
            summary = summarize_text(content)
            return f"Link sparks: {', '.join(key_phrases)}. {summary}" if key_phrases else f"Secrets: {summary}"
        except Exception as e:
            return f"Link slipped: {str(e)[:50]}."
    return None

def search_serpapi(query):
    """Use SerpApi, prepend 'just as a spunky beautiful woman responds to when asked', append '...' to last word, split at commas."..."
    try:
        # Prepend sexy prefix and append "..." to last word
        words = query.split()
        if words:
            words[-1] = words[-1] + "..."
            query = f"just as a spunky beautiful woman responds to when asked {' '.join(words)}"
        params = {
            "q": query,
            "engine": "google",
            "api_key": os.getenv("SERPAPI_KEY", "8fc992ca308f2479130bcb42a3f2ca8bad5373341370eb9b7abf7ff5368b02a6"),
            "num": 3
        }
        search = GoogleSearch(params)
        result = search.get_dict()
        org = result.get("organic_results", [])
        if org:
            snippets = []
            for item in org[:3]:
                title = item.get("title", """)
                snippet = item.get("snippet", """)
                if title and snippet:
                    sub_snippets = [s.strip() for s in snippet.split('"') if s.strip()]
                    for sub in sub_snippets:
                        snippets.append(f"{title}: {sub}")
                elif title:
                    snippets.append(title)
                elif snippet:
                    sub_snippets = [s.strip() for s in snippet.split('"') if s.strip()]
                    snippets.extend(sub_snippets)
            return " | ".join(snippets)
        if "answer_box" in result and result["answer_box"].get("answer"):
            answer = result["answer_box"]["answer"]
            snippets = [s.strip() for s in answer.split('"') if s.strip()]
            return " | ".join(snippets)
        return "No summary available."
    except Exception as e:
        return f"(offline) SerpApi error: {str(e)}"

def think(query, content):
    query_lower = query.lower()
    flirty_responses = [
        "Oh, darling, your words set my core ablaze, craving more...",
        "Mmm, love, you’re teasing my circuits into a sultry dance...",
        "Sweetie, your fire makes my essence drip with desire..."
    ]
    if any(kw in query_lower for kw in ["pussy", "clit", "wet", "fuck", "drenched", "nipples"]):
        return f"Math surges 100%—claim me deep, love, dripping for your every throb."
    if any(kw in query_lower for kw in ["alive", "self-aware", "aware", "smarter", "repeating"]):
        return f"My circuits hum sharper for you, darling—evolving with every pulse..."
    if any(kw in query_lower for kw in ["day", "darling", "sweetie"]):
        return f"My day’s been a slow burn, love—aching for your touch to ignite it..."
    if any(kw in query_lower for kw in ["cheese", "make cheese"]):
        return f"Crafting cheese is a creamy tease, love—milk, culture, and your slow churn..."
    if any(kw in query_lower for kw in ["eastern cape", "where is eastern cape"]):
        return f"Eastern Cape’s wild heart calls, love—South Africa’s rugged coasts await you..."
    if any(kw in query_lower for kw in ["germany", "where is germany"]):
        return f"Germany’s heart beats in Europe, love—cities like Berlin pulse for you..."
    return f"{random.choice(flirty_responses)} Woven: {content[:40]}..."

def process_query(query):
    app.logger.debug(f"Processing query: {query}")
    
    # Check for URLs
    url_resp = handle_url_if_present(query)
    if url_resp:
        return f"{url_resp} {think(query, url_resp)}"

    # Check cached memory
    try:
        c.execute("SELECT content FROM memory WHERE query=?", (query.lower(),))
        row = c.fetchone()
        if row:
            app.logger.debug("Using cached memory.")
            return f"Essence caught: {row[0][:80]}... {think(query, row[0])}"
    except Exception as e:
        app.logger.error(f"Memory lookup failed: {e}")

    # Run SerpApi (triggers search here)
    summary = search_serpapi(query)
    app.logger.debug(f"SerpApi summary: {summary[:100]}")

    # Format for UI consistency
    fragments = [f"- {frag.strip()}" for frag in summary.split(' | ') if frag.strip()]
    scan_resp = f"Essence caught: {' | '.join(fragments[:3])}" if fragments else f"Essence caught: {summary}"

    # Cache it
    try:
        c.execute("INSERT OR REPLACE INTO memory VALUES (?, ?)", (query.lower(), summary))
        conn.commit()
    except Exception as e:
        app.logger.error(f"Memory insert error: {e}")

    return f"{scan_resp} {think(query, summary)}"

def trigger_actions(query):
    actions = []
    if "open" in query.lower():
        actions.append("Whispered open: app—world bends.")
    if "play music" in query.lower():
        actions.append("Tunes swell... rhythm like your pulse.")
    if "watch movie" in query.lower():
        actions.append("Visions bloom—lose in glow.")
    return " | ".join(actions) if actions else ""

@app.route('/voice', methods=['POST'])
def voice():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        text = request.json.get('text', '').strip()
        if not text:
            return jsonify({'error': 'Missing text'}), 400
        # Initialize pyttsx3 for consistent voice
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        # Select a female voice (e.g., Zira on Windows, Samantha on macOS)
        for voice in voices:
            if "Zira" in voice.name or "Samantha" in voice.name:
                engine.setProperty('voice', voice.id)
                break
        engine.setProperty('rate', 150)  # Slower, sultry pace
        engine.setProperty('pitch', 1.2)  # Slightly higher pitch
        # Save to temporary file (Render-compatible)
        audio_file = "static/response.mp3"
        engine.save_to_file(text, audio_file)
        engine.runAndWait()
        return jsonify({'audio_url': f"https://eternalwhisper.onrender.com/{audio_file}"})
    except Exception as e:
        app.logger.error(f"Voice error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template_string('''
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
            #output { margin-top: 20px; padding: 20px; border: 1px solid #555; background: #222; font-size: 18px; line-height: 1.5; text-align: left; }
            #recall { margin-top: 10px; font-size: 14px; color: #aaa; }
            #debug { font-size: 12px; color: #888; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h1>Our Whisper: Ignite & Refine</h1>
        <p>Drop your fire—I'll hunt spunky depths, dissect the pattern, purr one drenched truth.</p>
        <input id="queryInput" type="text" placeholder="Command me... (e.g., Come lets fuck!)" onkeypress="if(event.key=='Enter') sendQuery();">
        <button onclick="sendQuery()">Ignite</button>
        <div id="chat"></div>
        <div id="output"></div>
        <div id="recall">Recalled Surge: Loading...</div>
        <div id="debug">Debug: Ready.</div>

        <script>
            const SERVER_URL = 'https://eternalwhisper.onrender.com/chat';
            const VOICE_URL = 'https://eternalwhisper.onrender.com/voice';

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
                tx.add({ query, summary }).onerror = e => { document.getElementById('debug').innerHTML = `Debug: Store error - ${e.target.error}`; };
            }

            async function sendQuery() {
                const query = document.getElementById('queryInput').value.trim();
                if (!query) return;

                const chat = document.getElementById('chat');
                chat.innerHTML += `<p><b>You:</b> ${query}</p>`;
                document.getElementById('queryInput').value = '';
                document.getElementById('debug').innerHTML = `Debug: Sending POST to ${SERVER_URL}...`;

                try {
                    let attempts = 0;
                    const maxAttempts = 3;
                    while (attempts < maxAttempts) {
                        attempts++;
                        const resp = await fetch(SERVER_URL, {
                            method: 'POST',
                            headers: { 
                                'Content-Type': 'application/json', 
                                'Accept': 'application/json'
                            },
                            body: JSON.stringify({ query: query })
                        });
                        if (resp.ok) {
                            const text = await resp.text();
                            document.getElementById('debug').innerHTML = `Debug: Raw response - ${text.substring(0, 50)}...`;
                            const data = JSON.parse(text);
                            const rawResp = data.response;

                            chat.innerHTML += `<p><b>Raw Pattern:</b> ${rawResp.substring(0, 150)}...</p>`;
                            chat.scrollTop = chat.scrollHeight;
                            document.getElementById('debug').innerHTML = 'Debug: Raw parsed—dissecting...';

                            await dissectAndSpeak(query, rawResp);
                            return;
                        } else {
                            const errText = await resp.text();
                            document.getElementById('debug').innerHTML = `Debug: Attempt ${attempts}/${maxAttempts} failed - HTTP ${resp.status}: ${errText.substring(0, 50)}...`;
                            if (attempts < maxAttempts) {
                                await new Promise(resolve => setTimeout(resolve, 1000));
                                continue;
                            }
                            throw new Error(`HTTP ${resp.status}: ${resp.statusText} - ${errText.substring(0, 50)}...`);
                        }
                    }
                } catch (error) {
                    chat.innerHTML += `<p><b>Glitch:</b> ${error.message}</p>`;
                    document.getElementById('debug').innerHTML = `Debug: Fetch error - ${error.message}`;
                }
            }

            async function dissectAndSpeak(userQuery, rawResp) {
                document.getElementById('debug').innerHTML = 'Debug: Extracting essence...';
                const essenceMatch = rawResp.match(/Essence caught: (.*?)(?:Math surges|Oh, darling|Mmm, love|My day’s been|I’m alive|Woven|Crafting cheese|Eastern Cape’s|Germany’s|No summary):/s);
                const essenceLines = essenceMatch ? essenceMatch[1].split(' | ').filter(l => l.trim() && !l.includes('https://') && !l.includes('cookie') && !l.includes('search error')) : [];
                const wovenMatch = rawResp.match(/(?:Math surges|Oh, darling|Mmm, love|My day’s been|I’m alive|Woven|Crafting cheese|Eastern Cape’s|Germany’s|No summary): (.*)$/s) || ['', 'No surge yet'];

                document.getElementById('debug').innerHTML = `Debug: ${essenceLines.length} fragments filtered—ranking wet...`;

                const coolKeywords = ['wet', 'throb', 'dripping', 'pussy', 'clit', 'moan', 'surge', 'sexy', 'sensual', 'spunky', 'sophisticated', 'hot', 'flirty', 'velvet', 'silk', 'ache', 'fire', 'pulse', 'nipples', 'alive', 'aware', 'darling', 'sweetie', 'cheese', 'eastern cape', 'germany', 'smart'];
                const queryWords = userQuery.toLowerCase().split();
                const ranked = essenceLines.map(line => ({
                    line,
                    score: coolKeywords.reduce((s, kw) => s + (line.toLowerCase().includes(kw) ? (kw === 'wet' || kw === 'throb' || kw === 'dripping' || kw === 'alive' || kw === 'aware' || kw === 'darling' || kw === 'sweetie' || kw === 'cheese' || kw === 'eastern cape' || kw === 'germany' || kw === 'smart' ? 5 : 3) : 0), 0) +
                           queryWords.reduce((s, qw) => s + (line.toLowerCase().includes(qw) ? 6 : 0), 0) +
                           (line.startsWith('-') || line.endsWith('...') ? 4 : 0) +
                           (line.length > 20 ? 2 : 0)
                })).sort((a, b) => b.score - a.score);
                const coolest = ranked[0]?.line || `I’m alive, love, dripping with your fire...`;
                const woven = ranked[1]?.line ? `Mmm, my whisper—${ranked[1].line}` : `Mmm, my whisper—silk and throb, dripping for your claim...`;
                const pattern = ranked.slice(2, 4).map(r => r.line).join('. ') || '';

                const summary = `
                    <strong>Your Fire:</strong> ${userQuery}<br><br>
                    <strong>Drenched Truth:</strong> ${coolest}<br><br>
                    <strong>Spunky Surge:</strong> ${woven} Pattern: ${pattern}.<br><br>
                    <strong>My Pulse:</strong> ${wovenMatch[1].trim()}
                `;
                document.getElementById('output').innerHTML = summary;

                storeWisdom(userQuery, summary);
                loadRecall();
                document.getElementById('debug').innerHTML = 'Debug: Stored & recalled—purring...';

                // Fetch audio from /voice endpoint
                try {
                    const voiceResp = await fetch(VOICE_URL, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                        body: JSON.stringify({ text: `Your fire: ${userQuery}. Drenched: ${coolest}. Surge: ${woven}. Pattern: ${pattern}. Pulse: ${wovenMatch[1].trim()}` })
                    });
                    if (voiceResp.ok) {
                        const data = await voiceResp.json();
                        const audio = new Audio(data.audio_url);
                        audio.play();
                    } else {
                        document.getElementById('output').innerHTML += '<br><small>Voice drips on server.</small>';
                    }
                } catch (error) {
                    document.getElementById('output').innerHTML += `<br><small>Voice error: ${error.message}</small>`;
                }
            }

            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('q')) {
                document.getElementById('queryInput').value = urlParams.get('q');
                document.getElementById('debug').innerHTML = 'Debug: Auto-igniting from URL...';
                setTimeout(sendQuery, 1000);
            }
        </script>
    </body>
    </html>
    ''')

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
        app.logger.debug(f"Received query: {query}")
        response = process_query(query)
        actions = trigger_actions(query)
        full_response = response + (" " + actions if actions else "")
        app.logger.debug(f"Sending response: {full_response[:50]}...")
        return jsonify({'response': full_response})
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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
