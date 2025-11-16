import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'app_user'
    MYSQL_PASSWORD = 'AppPass123!'
    MYSQL_DB = 'hotel_db'
    MYSQL_CURSORCLASS = 'DictCursor'
