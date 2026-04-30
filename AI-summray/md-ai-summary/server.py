import os
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

from services.fetch_data import fetch_dashboard_data
from services.process_data import process_data
from ai_agents import run_agents

app = Flask(__name__)
CORS(app)

STORAGE_DIR = "./storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

def generate_summary():
    try:
        raw = fetch_dashboard_data()
        processed = process_data(raw)
        summary = run_agents(processed)
        
        with open("./storage/summary.md", "w") as f:
            f.write(summary)
        
        print("Summary generated")
    except Exception as e:
        print(f"Error: {e}")

@app.route("/api/ai-summary-latest", methods=["GET"])
def get_summary():
    try:
        with open("./storage/summary.md", "r") as f:
            data = f.read()
        return jsonify({"summary": data})
    except:
        return jsonify({"summary": "No summary yet"})

@app.route("/api/run-summary", methods=["GET"])
def run_summary():
    generate_summary()
    return "Summary generated"

# Schedule daily run at 2 PM
scheduler = BackgroundScheduler()
scheduler.add_job(generate_summary, 'cron', hour=14, minute=0)
scheduler.start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"Server running on port {port}")
    app.run(host="0.0.0.0", port=port)
