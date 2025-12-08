from flask import Flask
from config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # make sure upload dir exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    from webapp.main import main_bp
    app.register_blueprint(main_bp)

    return app