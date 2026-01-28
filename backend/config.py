import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Configuración de la base de datos
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'galeria_diaria')
    DB_PORT = os.getenv('DB_PORT', '3306')
    
    # Configuración de la aplicación
    SECRET_KEY = os.getenv('SECRET_KEY', 'clave_secreta_para_desarrollo')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    
    # URL base para acceder a las imágenes
    BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')