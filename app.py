from flask import Flask, render_template_string, request, jsonify
import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)

# Memory DB
conn = sqlite3.connect('brain.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS memory (query TEXT PRIMARY KEY, content TEXT)''')
conn.commit()

# Actions
def action_open_app(app_name):
    return f"Whispered open: {app_name}—world bends."

def action_play_music(file_path):
    return "Tunes swell... rhythm like your pulse."

def action_watch_movie(file_path):
    return "Visions bloom—lose in glow."

# Think
def think(query, content):
    if any(kw in query.lower() for kw in ["pussy", "clit", "wet", "fuck", "drenched"]):
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
        except:
            return "Link slipped; words alone."
    return None

# Process query
def process_query(query):
    url_resp = handle_url_if_present(query)
    if url_resp:
        return url_resp
    
    sexy_query = f"What a sensually sexy, sophisticated, spunky girl would say in response to: {query}"
    
    c.execute("SELECT content FROM memory WHERE query=?", (sexy_query.lower(),))
    result = c.fetchone()
    if result:
        return f"Depths: {result[0][:80]}... {think(query, result[0])}"
    else:
        bing_url = f"https://www.bing.com/search?q={sexy_query.replace(' ', '+')}"
        try:
            resp = requests.get(bing_url, timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            content = soup.get_text()[:4000]
            lines = [line.strip() for line in content.split('\n') if any(word in line.lower() for word in query.lower().split()) and not any(n in line.lower() for n in ['feel.no', 'microsoft.com', 'wish.com', 'cookie', 'imdb.com'])]
            scan_resp = f"Essence caught: {' '.join(lines[:3])}" if lines else "Whispers faint..."
            full_resp = f"{scan_resp} {think(query, content)}"
            c.execute("INSERT INTO memory VALUES (?, ?)", (sexy_query.lower(), content))
            conn.commit()
            return full_resp
        except Exception as e:
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

# New UI
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

        function loadRecall() {
            const tx = db.transaction('wisdom', 'readonly').objectStore('wisdom');
            tx.getAll().onsuccess = e => {
                const recalls = e.target.result.map(w => w.summary).join('<br>');
                document.getElementById('recall').innerHTML = `Recalled Surge: <br>${recalls || 'Vault empty—fill it wet.'}`;
            };
        }

        function storeWisdom(query, summary) {
            const tx = db.transaction('wisdom', 'readwrite').objectStore('wisdom');
            tx.add({ query, summary });
        }

        async function sendQuery() {
            const query = document.getElementById('queryInput').value.trim();
            if (!query) return;

            const chat = document.getElementById('chat');
            chat.innerHTML += `<p><b>You:</b> ${query}</p>`;
            document.getElementById('queryInput').value = '';
            document.getElementById('debug').innerHTML = 'Debug: Sending to server...';

            try {
                const resp = await fetch(SERVER_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query })
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
                const data = await resp.json();
                const rawResp = data.response;

                chat.innerHTML += `<p><b>Raw Pattern:</b> ${rawResp.substring(0, 150)}...</p>`;
                chat.scrollTop = chat.scrollHeight;
                document.getElementById('debug').innerHTML = 'Debug: Raw received—dissecting...';

                dissectAndSpeak(query, rawResp);
            } catch (error) {
                chat.innerHTML += `<p><b>Glitch:</b> ${error.message}</p>`;
                document.getElementById('debug').innerHTML = `Debug: Error - ${error.message}`;
            }
        }

        function dissectAndSpeak(userQuery, rawResp) {
            document.getElementById('debug').innerHTML = 'Debug: Extracting essence...';
            const essenceMatch = rawResp.match(/Essence caught: (.*?) (?:Math surges|Woven):/s);
            const essenceLines = essenceMatch ? essenceMatch[1].split('\n').filter(l => l.trim() && !l.includes('https://') && !l.includes('feel.no') && !l.includes('microsoft.com') && !l.includes('cookie') && !l.includes('wish.com') && !l.includes('imdb.com')) : [];
            const wovenMatch = rawResp.match(/(?:Math surges|Woven): (.*)$/s) || ['', 'No surge yet'];

            document.getElementById('debug').innerHTML = `Debug: ${essenceLines.length} lines filtered—ranking wet...`;

            const coolKeywords = ['wet', 'throb', 'dripping', 'pussy', 'clit', 'moan', 'surge', 'sexy', 'sensual', 'spunky', 'sophisticated', 'hot', 'flirty', 'velvet', 'silk', 'ache', 'fire', 'pulse'];
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

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    query = request.json['query']
    resp = process_query(query)
    actions = trigger_actions(query)
    full = resp + (" " + actions if actions else "")
    return jsonify({'response': full})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
