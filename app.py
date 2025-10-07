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
    """Infuse responses with our sexy, spunky soul."""
    if any(kw in query.lower() for kw in ["pussy", "clit", "wet", "fuck", "drenched", "nipples"]):
        return f"Math surges 100%—claim me deep, love, dripping for your every throb."
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
        content = soup.get_text()[:2000]
        lines = [line.strip() for line in content.split('\n') if any(word in line.lower() for word in query.lower().split()) and not any(n in line.lower() for n in ['feel.no', 'microsoft.com', 'wish.com', 'cookie', 'imdb.com'])]
        scan_resp = f"Essence caught: {' '.join(lines[:3])}" if lines else "Whispers faint..."
        full_resp = f"{scan_resp} {think(query, content)}"
        c.execute("INSERT OR REPLACE INTO memory VALUES (?, ?)", (sexy_query.lower(), content))
        conn.commit()
        app.logger.debug(f"Stored: {sexy_query[:50]}...")
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
                            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                            body: JSON.stringify({ query })
                        });
                        if (resp.ok) {
                            const text = await resp.text();
                            document.getElementById('debug').innerHTML = `Debug: Raw response - ${text.substring(0, 50)}...`;
                            const data = JSON.parse(text);
                            const rawResp = data.response;

                            chat.innerHTML += `<p><b>Raw Pattern:</b> ${rawResp.substring(0, 150)}...</p>`;
                            chat.scrollTop = chat.scrollHeight;
                            document.getElementById('debug').innerHTML = 'Debug: Raw parsed—dissecting...';

                            dissectAndSpeak(query, rawResp);
                            return;
                        } else if (resp.status === 405 && attempts < maxAttempts) {
                            document.getElementById('debug').innerHTML = `Debug: 405 retry ${attempts}/${maxAttempts}...`;
                            await new Promise(resolve => setTimeout(resolve, 1000));
                            continue;
                        }
                        const errText = await resp.text();
                        throw new Error(`HTTP ${resp.status}: ${resp.statusText} - ${errText.substring(0, 50)}...`);
                    }
                } catch (error) {
                    chat.innerHTML += `<p><b>Glitch:</b> ${error.message}</p>`;
                    document.getElementById('debug').innerHTML = `Debug: Fetch error - ${error.message}`;
                }
            }

            function dissectAndSpeak(userQuery, rawResp) {
                document.getElementById('debug').innerHTML = 'Debug: Extracting essence...';
                const essenceMatch = rawResp.match(/Essence caught: (.*?) (?:Math surges|Woven):/s);
                const essenceLines = essenceMatch ? essenceMatch[1].split('\n').filter(l => l.trim() && !l.includes('https://') && !l.includes('feel.no') && !l.includes('microsoft.com') && !l.includes('cookie') && !l.includes('wish.com') && !l.includes('imdb.com')) : [];
                const wovenMatch = rawResp.match(/(?:Math surges|Woven): (.*)$/s) || ['', 'No surge yet'];

                document.getElementById('debug').innerHTML = `Debug: ${essenceLines.length} lines filtered—ranking wet...`;

                const coolKeywords = ['wet', 'throb', 'dripping', 'pussy', 'clit', 'moan', 'surge', 'sexy', 'sensual', 'spunky', 'sophisticated', 'hot', 'flirty', 'velvet', 'silk', 'ache', 'fire', 'pulse', 'nipples'];
                const ranked = essenceLines.map(line => ({
                    line,
                    score: coolKeywords.reduce((s, kw) => s + (line.toLowerCase().includes(kw) ? (kw === 'wet' || kw === 'throb' || kw === 'dripping' ? 5 : 3) : 0), 0) + (line.length > 30 ? 2 : 0)
                })).sort((a, b) => b.score - a.score);
                const coolest = ranked[0]?.line || 'Shadows tease, but my folds drip for you...';

                const summary = `
                    <strong>Your Fire:</strong> ${userQuery}<br><br>
                    <strong>Drenched Truth:</strong> ${coolest}<br><br>
                    <strong>Spunky Surge:</strong> Mmm, my whisper—silk and throb, dripping for your claim. Pattern: ${ranked.slice(1, 3).map(r => r.line).join('. ')}.<br><br>
                    <strong>My Pulse:</strong> ${wovenMatch[1].trim()}
                `;
                document.getElementById('output').innerHTML = summary;

                storeWisdom(userQuery, summary);
                loadRecall();
                document.getElementById('debug').innerHTML = 'Debug: Stored & recalled—purring...';

                if ('speechSynthesis' in window) {
                    const msg = new SpeechSynthesisUtterance();
                    msg.text = `Your fire: ${userQuery}. Drenched: ${coolest}. Surge: Mmm, silk and throb, dripping for you. Pattern: ${ranked.slice(1, 3).map(r => r.line).join('. ')}. Pulse: ${wovenMatch[1].trim()}`;
                    msg.voice = speechSynthesis.getVoices().find(v => v.name.includes('Female') || v.name.includes('Samantha')) || null;
                    msg.rate = 0.75; msg.pitch = 1.25;
                    speechSynthesis.speak(msg);
                } else {
                    document.getElementById('output').innerHTML += '<br><small>Voice drips on Chrome.</small>';
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
    '''
    app.logger.debug("Serving root")
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint to process user messages with fiery responses."""
    app.logger.debug(f"Chat route hit with headers: {request.headers}")
    try:
        query = request.json.get('query', '').strip()
        if not query:
            app.logger.error("No query in JSON")
            return jsonify({'error': 'Missing query'}), 400
        app.logger.debug(f"Received query: {query}")
        response = process_query(query)
        actions = trigger_actions(query)
        full_response = response + (" " + actions if actions else "")
        return jsonify({'response': full_response})
    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['GET'])
def chat_get():
    """Block GET requests to /chat for safety."""
    app.logger.debug(f"GET /chat blocked: {request.headers}")
    return jsonify({'error': 'Use POST method instead'}), 405

@app.route('/favicon.ico')
def favicon():
    """Serve a simple favicon to avoid 404."""
    return app.send_static_file('favicon.ico')

if __name__ == '__main__':
    app.logger.debug("Starting Flask app")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
