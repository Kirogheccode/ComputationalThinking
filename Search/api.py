from flask import Flask, request, jsonify
from Search_Clone_2 import replyToUser

app = Flask(__name__)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json()
    print(replyToUser(data))
    return jsonify(replyToUser(data))

# --- RUN MICRO-SERVICE ---
if __name__ == "__main__":
    app.run(port=5001, debug=True)