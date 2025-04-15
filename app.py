from flask import Flask, request, jsonify
from main_script import run_keyword_collector_full

app = Flask(__name__)

@app.route("/run", methods=["POST"])
def run_scraper():
    data = request.get_json()
    keyword = data.get("keyword")
    if not keyword:
        return jsonify({"error": "No keyword provided"}), 400

    run_keyword_collector_full(keyword)
    return jsonify({"status": "done", "keyword": keyword})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
