from flask import Flask, send_from_directory
from flask_cors import CORS

from backend.database import init_db, seed_demo_data
from backend.routes import api_bp


def create_app():
    app = Flask(__name__, static_folder="../frontend")
    CORS(app)
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        return send_from_directory("frontend", "index.html")

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory("frontend", "favicon.ico", mimetype="image/x-icon")

    @app.route("/<path:filename>")
    def serve_frontend(filename):
        return send_from_directory("frontend", filename)

    return app


if __name__ == "__main__":
    init_db()
    seed_demo_data()
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
