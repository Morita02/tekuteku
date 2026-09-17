"""
extensions.py
─────────────
Flask拡張のインスタンスをここだけで定義する。
app.py / models.py / routes/*.py はここから db をインポートすることで
循環インポートを防ぐ。
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
