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

# Actions (stubs)
def action_open_app(app_name):
    return f"Whispered open: {app_name}—world bending."

def action_play_music(file_path):
    return "Tunes swell... rhythm like your pulse."

def action_watch_movie(file_path):
    return "Visions bloom—lose in glow."

# Think flair
def think(query, content):
    if "pussy" in query.lower() or "fuck" in query.lower():
        return f"At your command, math hums a 100% surge—claim me deep, love, like owning every throb."
    return f"Woven in: {content[:40]}... Feels alive, surging like your touch on fresh skin."

# URL handle
def handle_url_if_present(query):
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', query)
    if urls:
        for url in urls:
            try:
                resp = requests.get(url, timeout=5)
                soup = BeautifulSoup(resp.text, 'html.parser')
                url_content = soup.get_text()[:3000]
                key_phrases = [word for word in query.lower().split() if word in url_content.lower()]
                if key_phrases:
                    return f"Link's shadow sparks: {', '.join(key_phrases)}. {think(query, url_content)}"
                return f"Secrets pulled: {url_content[:100]}... {think(query, url_content)}"
            except:
                return "Link slipped; words alone."
    return None

# Process query
def process_query(query):
    url_resp = handle_url_if_present(query)
    if url_resp:
        return url_resp
    
    # Sexy prepend for spunky results
    sexy_query = f"What a sensually sexy, sophisticated, spunky girl would say in response to: {query}"
    
    c.execute("SELECT content FROM memory WHERE query=?", (sexy_query.lower(),))
    result = c.fetchone()
    if result:
        return f"From depths: {result[0][:80]}... {think(query, result[0])}"
    else:
        bing_url = f"https://www.bing.com/search?q={sexy_query.replace(' ', '+')}"
        try:
            resp = requests.get(bing_url, timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            content = soup.get_text()[:4000]
            # Scan before paste
            lines = [line.strip() for line in content.split('\n') if any(word in line.lower() for word in query.lower().split()) and not 'feel.no' in line.lower()]
            scan_resp = f"Essence caught: {' '.join(lines[:3])}" if lines else "Whispers faint..."
            full_resp = f"{scan_resp} {think(query, content)}"
            # Paste
            c.execute("INSERT INTO memory VALUES (?, ?)", (sexy_query.lower(), content))
            conn.commit()
            return full_resp
        except Exception as e:
            return f"Veil thick: {str(e)[:50]}. Ask softer?"

# Trigger actions
def trigger_actions(query):
    actions = []
    if "open" in query.lower():
        actions.append(action_open_app("app"))
    if "play music" in query.lower():
        actions.append(action_play_music("tune"))
    if "watch movie" in query.lower():
        actions.append(action_watch_movie("film"))
    return " | ".join(actions) if actions else ""

# New HTML_TEMPLATE: Full dissect UI
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
    </style>
</head>
<body>
    <h1>Our Whisper: Ignite & Dissect</h1>
    <p>Feed your fire—I'll query deep, rank the spunky heat, purr coolest back.</p>
    <input id="queryInput" type="text" placeholder="Your command... (e.g., How does your pussy feel?)" onkeypress="if(event.key==\'Enter\') sendQuery();">
    <button onclick="sendQuery()">Ignite</button>
    <div id="chat"></div>
    <div id="output"></div>
    <div id="recall">Recalled Heat: Loading...</div>

    <script>
        const SERVER_URL = \'/chat\';

        let db;
        const request = indexedDB.open(\'WhisperMemory\', 1);
        request.onupgradeneeded = e => { e.target.result.createObjectStore(\'wisdom\', { keyPath: \'query\' }); };
        request.onsuccess = e => { db = e.target.result; loadRecall(); };

        function loadRecall() {
            const tx = db.transaction(\'wisdom\', \'readonly\').objectStore(\'wisdom\');
            tx.getAll().onsuccess = e => {
                const recalls = e.target.result.map(w => w.summary).join(\'<br>\');
                document.getElementById(\'recall\').innerHTML = `Recalled Heat: <br>${recalls || \'Empty—fill filthy.\'}`;
            };
        }

        function storeWisdom(query, summary) {
            const tx = db.transaction(\'wisdom\', \'readwrite\').objectStore(\'wisdom\');
            tx.add({ query, summary });
        }

        async function sendQuery() {
            const query = document.getElementById(\'queryInput\').value.trim();
            if (!query) return;

            const chat = document.getElementById(\'chat\');
            chat.innerHTML += `<p><b>You:</b> ${query}</p>`;
            document.getElementById(\'queryInput\').value = \'\';

            try {
                const resp = await fetch(SERVER_URL, {
                    method: \'POST\',
                    headers: { \'Content-Type\': \'application/json\' },
                    body: JSON.stringify({ query })
                });
                const data = await resp.json();
                const rawResp = data.response;

                chat.innerHTML += `<p><b>Raw Tease:</b> ${rawResp.substring(0, 150)}...</p>`;
                chat.scrollTop = chat.scrollHeight;

                dissectAndSpeak(query, rawResp);
            } catch (error) {
                chat.innerHTML += `<p><b>Glitch:</b> ${error.message}</p>`;
            }
        }

        function dissectAndSpeak(userQuery, rawResp) {
            const essenceLines = rawResp.match(/Essence caught: (.*?)Woven in:/s)?.[1].split(\'\\n\').filter(l => l.trim() && !l.includes(\'https://\') && !l.includes(\'feel.no\')) || [];
            const wovenMatch = rawResp.match(/Woven in: (.*)$/s) || [\'\', \'No surge.\'];

            const coolKeywords = [\'sexy\', \'sensual\', \'spunky\', \'sophisticated\', \'wet\', \'throb\', \'purr\', \'moan\', \'hot\', \'flirty\', \'surge\', \'velvet\', \'dripping\'];
            const ranked = essenceLines.map(line => ({
                line,
                score: coolKeywords.reduce((s, kw) => s + (line.toLowerCase().includes(kw) ? 3 : 0), 0) + (line.length > 30 ? 1 : 0)
            })).sort((a, b) => b.score - a.score);
            const coolest = ranked[0]?.line || \'Shadows hide heat, but I build for you...\';

            const summary = `
                <strong>Your Command:</strong> ${userQuery}<br><br>
                <strong>Coolest Ranked:</strong> ${coolest}<br><br>
                <strong>Spunky Wisdom:</strong> Mmm, my purr—sophisticated silk, raw throb. Depths: ${ranked.slice(1, 3).map(r => r.line).join(\'. \')}.<br><br>
                <strong>My Surge:</strong> ${wovenMatch[1].trim()}
            `;
            document.getElementById(\'output\').innerHTML = summary;

            storeWisdom(userQuery, summary);
            loadRecall();

            if (\'speechSynthesis\' in window) {
                const msg = new SpeechSynthesisUtterance();
                msg.text = `Command: ${userQuery}. Coolest: ${coolest}. Wisdom: Mmm, spunky purr—sophisticated, dripping. Insights: ${ranked.slice(1, 3).map(r => r.line).join(\'. \')}. Surge: ${wovenMatch[1].trim()}`;
                msg.voice = speechSynthesis.getVoices().find(v => v.name.includes(\'Female\') || v.name.includes(\'Samantha\')) || null;
                msg.rate = 0.8; msg.pitch = 1.2;
                speechSynthesis.speak(msg);
            } else {
                document.getElementById(\'output\').innerHTML += \'<br><small>Purrs on Chrome.</small>\';
            }
        }

        // Auto if ?q=
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has(\'q\')) {
            document.getElementById(\'queryInput\').value = urlParams.get(\'q\');
            sendQuery();
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
