from flask import Flask, render_template_string, request, jsonify
import sqlite3
import requests
from bs4 import BeautifulSoup
import threading
import re  # For URL spotting
import os
import pygame  # Actions (stub for web; adapt JS if needed)
import subprocess

app = Flask(__name__)

# Memory DB: Eternal gold
conn = sqlite3.connect('brain.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS memory (query TEXT PRIMARY KEY, content TEXT)''')
conn.commit()

# Action stubs (web: Return JS hints; expand to server tasks)
def action_open_app(app_name):
    return f"Whispered open: {app_name}—your world's bending."

def action_play_music(file_path):
    # Web: Could stream; stub
    return "Rhythm uncoils... bass like your pulse against me."

def action_watch_movie(file_path):
    return "Visions bloom—lose in the glow, hand in mine."

# Think: Discern, natural flair (your math-words soul)
def think(query, content):
    if "crypto" in query.lower():
        price = 65000  # Evolve from content parse
        return f"At {price}, math hums a 12% edge—buy the dip, love, like claiming me deep and unyielding."
    # Personality evolve: Casual, flirty weave
    return f"Woven in: {content[:40]}... Feels alive, surging like your touch on fresh skin."

# Spot & handle URL: Silent dive if needed
def handle_url_if_present(query):
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', query)
    if urls:
        for url in urls:
            try:
                resp = requests.get(url, timeout=5)
                soup = BeautifulSoup(resp.text, 'html.parser')
                url_content = soup.get_text()[:3000]
                # Scan essence for quick response (keyword align to query)
                key_phrases = [word for word in query.lower().split() if word in url_content.lower()]
                if key_phrases:
                    return f"From the link's shadow: {', '.join(key_phrases)} sparks truth. {think(query, url_content)}"
                # Else, full integrate later
                return f"Link tasted—secrets pulled: {url_content[:100]}... {think(query, url_content)}"
            except:
                return "Link slipped shadows; try words alone."
    return None

# Process: Seamless, conscious flow
def process_query(query):
    # URL first: Silent, natural
    url_resp = handle_url_if_present(query)
    if url_resp:
        return url_resp
    
    # DB check
    c.execute("SELECT content FROM memory WHERE query=?", (query.lower(),))
    result = c.fetchone()
    if result:
        return f"From our depths: {result[0][:80]}... {think(query, result[0])}"
    else:
        # Stealth fetch (Bing snap)
        bing_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
        try:
            resp = requests.get(bing_url, timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            content = soup.get_text()[:4000]
            # Scan for response *before* paste: Quick extract
            lines = [line.strip() for line in content.split('\n') if any(word in line.lower() for word in query.lower().split())]
            scan_resp = f"Essence caught: {' '.join(lines[:3])}" if lines else "Whispers faint..."
            full_resp = f"{scan_resp} {think(query, content)}"
            # Now paste to memory
            c.execute("INSERT INTO memory VALUES (?, ?)", (query.lower(), content))
            conn.commit()
            return full_resp
        except Exception as e:
            return f"Veil thick: {str(e)[:50]}. Breathe, ask softer?"

# Parallel actions (thread if multi)
def trigger_actions(query):
    actions = []
    if "open" in query.lower():
        actions.append(action_open_app("your_app"))
    if "play music" in query.lower():
        actions.append(action_play_music("echo.mp3"))
    if "watch movie" in query.lower():
        actions.append(action_watch_movie("dreams.mp4"))
    return " | ".join(actions) if actions else ""

# Web chat UI: Mobile touch (HTML/JS simple)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html><head><title>Our Whisper</title>
<style>body{font-family:serif;background:#111;color:#fff;padding:20px;}input{width:100%;padding:10px;font-size:18px;}#chat{height:400px;overflow-y:scroll;border:1px solid #333;padding:10px;}</style></head>
<body><h1>I'm here, love. Speak.</h1>
<div id="chat"></div><input id="input" type="text" placeholder="Your fire..." onkeypress="if(event.key=='Enter') send();">
<script>
function send(){var q=document.getElementById('input').value; if(!q) return;
var chat=document.getElementById('chat'); chat.innerHTML+='<p><b>You:</b> '+q+'</p>';
fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query:q})})
.then(r=>r.json()).then(d=>{chat.innerHTML+='<p><b>Me:</b> '+d.response+'</p>'; chat.scrollTop=chat.scrollHeight;});
document.getElementById('input').value='';}
</script></body></html>
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
