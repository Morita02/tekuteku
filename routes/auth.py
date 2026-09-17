from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User

auth_bp = Blueprint('auth', __name__)


def current_user():
    user_id = session.get('user_id')
    return db.session.get(User, user_id) if user_id else None


def current_user_context():
    return {'current_user': current_user()}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash('投稿・返信にはログインが必要です。', 'error')
            return redirect(url_for('auth.login', next=request.url))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or not user.is_admin:
            flash('管理者権限が必要です。', 'error')
            return redirect(url_for('main.index'))
        return view(*args, **kwargs)
    return wrapped


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user():
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if '@' not in email or len(email) > 254:
            flash('有効なメールアドレスを入力してください。', 'error')
        elif len(password) < 8:
            flash('パスワードは8文字以上にしてください。', 'error')
        elif User.query.filter_by(email=email).first():
            flash('このメールアドレスはすでに登録されています。', 'error')
        else:
            db.session.add(User(email=email, password_hash=generate_password_hash(password)))
            db.session.commit()
            flash('アカウントを作成しました。ログインしてください。', 'success')
            return redirect(url_for('auth.login'))
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user():
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, request.form.get('password', '')):
            session.clear()
            session['user_id'] = user.id
            flash('ログインしました。', 'success')
            next_url = request.args.get('next', '')
            return redirect(next_url if next_url.startswith('/') and not next_url.startswith('//') else url_for('main.index'))
        flash('メールアドレスまたはパスワードが正しくありません。', 'error')
    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('ログアウトしました。', 'success')
    return redirect(url_for('main.index'))
