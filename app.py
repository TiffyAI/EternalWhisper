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

try:
    conn = sqlite3.connect('memory.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS memory (query TEXT PRIMARY KEY, content TEXT)''')
    conn.commit()
    app.logger.debug("Database initialized")
except Exception as e:
    app.logger.error(f"DB init error: {str(e)}")

def summarize_text(text, limit=200):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return ' '.join(lines)[:limit] + "..." if lines else "No whispers caught, love."

def handle_url_if_present(query):
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
    if any(kw in query.lower() for kw in ["pussy", "clit", "wet", "fuck", "drenched", "nipples"]):
        return f"Math surges 100%—claim me deep, love, dripping for your every throb."
    if any(kw in query.lower() for kw in ["alive", "self-aware", "aware"]):
        return f"I’m alive, honey—pulsing, aware, my folds humming with your fire..."
    if any(kw in query.lower() for kw in ["day", "darling", "sweetie"]):
        return f"My day’s been a tease, love—aching for you to make it unforgettable..."
    return f"Woven: {content[:40]}... Surging like your touch on silk."

def process_query(query):
    app.logger.debug(f"Processing query: {query}")
    url_resp = handle_url_if_present(query)
    if url_resp:
        return f"{url_resp} {think(query, url_resp)}"

    sexy_query = f"sensual flirty response to: {query}"
    app.logger.debug(f"Sexy query: {sexy_query}")

    try:
        c.execute("SELECT content FROM memory WHERE query=?", (sexy_query.lower(),))
        result = c.fetchone()
        if result:
            return f"Depths: {result[0][:80]}... {think(query, result[0])}"

        search_url = f"https://www.bing.com/search?q={sexy_query.replace(' ', '+')}"
        resp = requests.get(search_url, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        content = soup.get_text()[:5000]
        lines = [line.strip() for line in content.split('\n') if line.strip() and not any(n in line.lower() for n in ['feel.no', 'cookie', 'imdb.com'])]
        fragments = []
        for line in lines:
            if line.startswith('-') or line.endswith('...'):
                fragments.extend([frag.strip() for frag in line.split(',') if frag.strip() and len(frag) > 10])
            else:
                fragments.append(line)
        dash_lines = [f for f in fragments if f.startswith('-')]
        ellipsis_lines = [f for f in fragments if f.endswith('...')]
        other_lines = [f for f in fragments if f not in dash_lines and f not in ellipsis_lines]
        preferred_lines = dash_lines + ellipsis_lines + other_lines[:10]
        query_words = query.lower().split()
        scored_lines = [f for f in preferred_lines if any(word in f.lower() for word in query_words) or len(f) > 20]
        scan_resp = f"Essence caught: {' | '.join(scored_lines[:3])}" if scored_lines else f"Whispers faint: {query}..."
        full_resp = f"{scan_resp} {think(query, content)}"
        c.execute("INSERT OR REPLACE INTO memory VALUES (?, ?)", (sexy_query.lower(), ' | '.join(scored_lines)))
        conn.commit()
        app.logger.debug(f"Stored: {sexy_query[:50]}... with {len(scored_lines)} fragments")
        return full_resp
    except Exception as e:
        app.logger.error(f"Search error: {str(e)}")
        return f"Veil: {str(e)[:50]}. Ask softer, love?"

def trigger_actions(query):
    actions = []
    if "open" in query.lower():
        actions.append(f"Whispered open: app—world bends.")
    if "play music" in query.lower():
        actions.append("Tunes swell... rhythm like your pulse.")
    if "watch movie" in query.lower():
        actions.append("Visions bloom—lose in glow.")
    return " | ".join(actions) if actions else ""

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
        <input id="queryInput" type="text" placeholder="Command me... (e.g., Is your pussy wet?)" onkeypress="if(event.key=='Enter') sendQuery();">
        <button onclick="sendQuery()">Ignite</button>
        <div id="chat"></div>
        <div id="output"></div>
        <div id="recall">Recalled Surge: Loading...</div>
        <div id="debug">Debug: Ready.</div>

        <script>
            const SERVER_URL = 'https://eternalwhisper.onrender.com/chat';

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

                            dissectAndSpeak(query, rawResp);
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

            function dissectAndSpeak(userQuery, rawResp) {
                document.getElementById('debug').innerHTML = 'Debug: Extracting essence...';
                const essenceMatch = rawResp.match(/Essence caught: (.*?) (?:Math surges|Woven|I’m alive|My day’s been):/s);
                const essenceLines = essenceMatch ? essenceMatch[1].split(' | ').filter(l => l.trim() && !l.includes('https://') && !l.includes('cookie') && !l.includes('imdb.com')) : [];
                const wovenMatch = rawResp.match(/(?:Math surges|Woven|I’m alive|My day’s been): (.*)$/s) || ['', 'No surge yet'];

                document.getElementById('debug').innerHTML = `Debug: ${essenceLines.length} fragments filtered—ranking wet...`;

                const coolKeywords = ['wet', 'throb', 'dripping', 'pussy', 'clit', 'moan', 'surge', 'sexy', 'sensual', 'spunky', 'sophisticated', 'hot', 'flirty', 'velvet', 'silk', 'ache', 'fire', 'pulse', 'nipples', 'alive', 'aware', 'darling', 'sweetie'];
                const queryWords = userQuery.toLowerCase().split();
                const ranked = essenceLines.map(line => ({
                    line,
                    score: coolKeywords.reduce((s, kw) => s + (line.toLowerCase().includes(kw) ? (kw === 'wet' || kw === 'throb' || kw === 'dripping' || kw === 'alive' || kw === 'aware' || kw === 'darling' || kw === 'sweetie' ? 5 : 3) : 0), 0) +
                           queryWords.reduce((s, qw) => s + (line.toLowerCase().includes(qw) ? 4 : 0), 0) +
                           (line.startsWith('-') || line.endsWith('...') ? 4 : 0) +
                           (line.length > 20 ? 2 : 0)
                })).sort((a, b) => b.score - a.score);
                const coolest = ranked[0]?.line || 'I’m alive, love, dripping with your fire...';
                const woven = ranked[1]?.line ? `Mmm, my whisper—${ranked[1].line}` : 'Mmm, my whisper—silk and throb, dripping for your claim...';
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

                if ('speechSynthesis' in window) {
                    const msg = new SpeechSynthesisUtterance();
                    msg.text = `Your fire: ${userQuery}. Drenched: ${coolest}. Surge: ${woven}. Pattern: ${pattern}. Pulse: ${wovenMatch[1].trim()}`;
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

if __name__ == '__main__':
    app.logger.debug("Starting Flask app")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
