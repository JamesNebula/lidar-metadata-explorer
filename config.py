import os 
import secrets

class Config:
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16MB
    ALLOWED_EXTENSIONS = {'las', 'laz'}
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(16)