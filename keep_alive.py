from flask import Flask, jsonify
import threading
import time
import os
import logging

# Disable Flask logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "alive",
        "message": "Music Bot is running!",
        "uptime": time.time(),
        "version": "1.0.0"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": time.time()
    })

@app.route('/stats')
def stats():
    return jsonify({
        "status": "running",
        "memory_usage": "N/A",
        "cpu_usage": "N/A",
        "uptime": time.time()
    })

def run():
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()
    print(f"🌐 Keep alive server started on port {os.environ.get('PORT', 8000)}")

if __name__ == "__main__":
    keep_alive()
