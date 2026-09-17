"""
app.py
──────
Flaskアプリ本体。
  extensions.py で db を生成 → models.py でテーブル定義 → routes/ でルート登録
  という一方向の依存にすることで循環インポートを防ぐ。

起動方法:
    pip install -r requirements.txt
    python app.py
"""

import os
import webbrowser
import threading

from flask import Flask, send_from_directory
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash
from sqlalchemy import text
from extensions import db          # ← db はここから来る

# ──────────────────────────────────────────────
# アプリ初期化
# ──────────────────────────────────────────────
data_dir = os.environ.get('TEKUTEKU_DATA_DIR')
app = Flask(__name__, **({'instance_path': os.path.abspath(data_dir)} if data_dir else {}))
is_render = os.environ.get('RENDER') == 'true'
if is_render:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    if not os.environ.get('SECRET_KEY'):
        raise RuntimeError('Set SECRET_KEY in the Render environment before starting.')
os.makedirs(app.instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI']    = 'sqlite:///tekuteku.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER']             = (os.path.join(app.instance_path, 'uploads') if data_dir else os.path.join(app.root_path, 'static', 'uploads'))
app.config['MAX_CONTENT_LENGTH']        = 16 * 1024 * 1024   # 16MB

app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=is_render,
    DEMO_MODE=os.environ.get('DEMO_MODE') == '1',
    SESSION_COOKIE_SAMESITE='Lax',
)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
CSRFProtect(app)


@app.route('/healthz')
def healthz():
    return {'status': 'ok'}


@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    response = send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'none'; sandbox"
    return response


@app.after_request
def response_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    if app.config['DEMO_MODE']:
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response

# db を app に紐付け（extensions.py で生成済みのインスタンスを初期化）
db.init_app(app)

# ──────────────────────────────────────────────
# モデル・ルートの登録
# （app と db が確定してから import する）
# ──────────────────────────────────────────────
with app.app_context():
    import models  # noqa: F401  テーブル定義を読み込む
    from models import Location, User

    from routes.main  import main_bp
    from routes.posts import posts_bp
    from routes.map   import map_bp
    from routes.api   import api_bp
    from routes.settings import settings_bp, theme_context
    from routes.auth import auth_bp, current_user_context

    app.register_blueprint(main_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(auth_bp)

    # テーマ設定を全ページのテンプレートで使えるようにする
    app.context_processor(theme_context)
    app.context_processor(current_user_context)

    db.create_all()

    # Existing SQLite installations predate account and event-deadline fields.
    # Add them in place so existing posts remain available.
    columns = {row[1] for row in db.session.execute(text("PRAGMA table_info(info_post)"))}
    if 'deadline' not in columns:
        db.session.execute(text('ALTER TABLE info_post ADD COLUMN deadline DATETIME'))
    if 'author_id' not in columns:
        db.session.execute(text('ALTER TABLE info_post ADD COLUMN author_id INTEGER'))
    if 'location_id' not in columns:
        db.session.execute(text('ALTER TABLE info_post ADD COLUMN location_id INTEGER'))
    location_columns = {row[1] for row in db.session.execute(text("PRAGMA table_info(location)"))}
    if 'author_id' not in location_columns:
        db.session.execute(text('ALTER TABLE location ADD COLUMN author_id INTEGER'))
    reply_columns = {row[1] for row in db.session.execute(text("PRAGMA table_info(reply)"))}
    if 'author_id' not in reply_columns:
        db.session.execute(text('ALTER TABLE reply ADD COLUMN author_id INTEGER'))
    user_columns = {row[1] for row in db.session.execute(text("PRAGMA table_info(user)"))}
    if 'is_admin' not in user_columns:
        db.session.execute(text('ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0'))
    if 'display_name' not in user_columns:
        db.session.execute(text('ALTER TABLE user ADD COLUMN display_name VARCHAR(50)'))
    if 'level' not in user_columns:
        db.session.execute(text('ALTER TABLE user ADD COLUMN level INTEGER NOT NULL DEFAULT 1'))
        db.session.execute(text(
            'UPDATE user SET level = 1 + '
            '(SELECT COUNT(*) FROM info_post WHERE info_post.author_id = user.id)'
        ))

    # Render無料版では再起動時にSQLiteの内容が失われるため、管理者アカウントを
    # 起動ごとに確認する。初期パスワードは公開ソースに書かず、環境変数からだけ読む。
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@akita').strip().lower()
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if admin_password:
        admin_user = User.query.filter_by(email=admin_email).first()
        if not admin_user:
            db.session.add(User(
                email=admin_email,
                password_hash=generate_password_hash(admin_password),
                display_name='Admin',
                is_admin=True,
            ))
        else:
            admin_user.is_admin = True

    # 初期表示用の代表的な場所。名前で確認して重複登録を防ぐ。
    initial_locations = (
        {
            'name': '赤居文庫',
            'type': '飲食店',
            'lat': 39.7184,
            'lng': 140.1241,
            'city': '秋田市',
            'description': 'Cafe 赤居文庫（秋田市中通4-6-16）',
        },
        {
            'name': 'バイロカフェ',
            'type': '飲食店',
            'lat': 39.7161,
            'lng': 140.1117,
            'city': '秋田市',
            'description': 'BAIRO CAFE（秋田市大町5-2-33）',
        },
        {
            'name': 'セリオン',
            'type': '観光地',
            'lat': 39.75286,
            'lng': 140.06138,
            'city': '秋田市',
            'description': '道の駅あきた港 ポートタワー・セリオン（秋田市土崎港西1-9-1）',
        },
    )
    for location_data in initial_locations:
        if not Location.query.filter_by(name=location_data['name']).first():
            db.session.add(Location(**location_data))
    db.session.commit()

# ──────────────────────────────────────────────
# 起動
# ──────────────────────────────────────────────
if __name__ == '__main__':
    threading.Timer(1.0, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
