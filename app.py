# app.py
from flask import Flask
from flask_cors import CORS
from database import init_db
from routes import history_bp

app = Flask(__name__)
CORS(app)

# Initialize database on startup
init_db()

# Register Routes
app.register_blueprint(history_bp, url_prefix="/api/history")

if __name__ == "__main__":
    app.run(debug=True)
