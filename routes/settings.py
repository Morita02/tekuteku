"""
routes/settings.py  ── 「もっとかわいくする設定」ページ

設定の実体（色・昼夜・ことば）はすべて Cookie に保存され、
static/js/theme.js が全ページで読み込んで適用する。
このブループリントは設定 UI のページを出すだけ。
"""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import ImportCandidate, InfoPost
from routes.auth import admin_required, current_user, login_required

# ──────────────────────────────────────────────
# テーマの定義（theme.js の COLOR_PALETTE と対になっている）
#   c  … テーマカラー
#   fg … その色の上に乗せる文字色
# ──────────────────────────────────────────────
COLOR_PALETTE = {
    'さくらピンク':     {'c': '#ff8fa3', 'fg': '#ffffff'},
    'なまはげレッド':   {'c': '#e63946', 'fg': '#ffffff'},
    'ふきいろグリーン': {'c': '#11caa0', 'fg': '#ffffff'},
    'ババヘライエロー': {'c': '#ffb703', 'fg': '#443300'},
    '日本海ブルー':     {'c': '#219ebc', 'fg': '#ffffff'},
}
DEFAULT_COLOR = '#ff8fa3'


def theme_context():
    """
    Cookie のテーマ設定を全テンプレートへ渡す（app.py で context_processor に登録）。

    これを <html> タグに最初から焼き込んでおくことで、JS が動くまでの一瞬
    既定色が見えてしまう「チラつき」を防ぐ。
    Cookie は利用者が自由に書き換えられるので、必ずパレット内の値に丸めてから使う
    （style 属性へ素通しすると CSS インジェクションになる）。
    """
    known = {v['c']: v['fg'] for v in COLOR_PALETTE.values()}
    color = request.cookies.get('theme_color', DEFAULT_COLOR)
    if color not in known:
        color = DEFAULT_COLOR
    return {
        'theme_color':   color,
        'theme_on_main': known[color],
        'theme_mode':    'dark' if request.cookies.get('dark_mode') == '1' else 'light',
    }


settings_bp = Blueprint(
    'settings',
    __name__,
    url_prefix='/settings',
)


@settings_bp.route('/')
@login_required
def settings_page():
    return render_template('settings/index.html', user=current_user())


@settings_bp.route('/account', methods=['POST'])
@login_required
def update_account():
    user = current_user()
    display_name = request.form.get('display_name', '').strip()
    if not display_name:
        flash('表示名を入力してください。', 'error')
    elif len(display_name) > 50:
        flash('表示名は50文字以内にしてください。', 'error')
    else:
        user.display_name = display_name
        db.session.commit()
        flash('表示名を更新しました。', 'success')
    return redirect(url_for('settings.settings_page'))


@settings_bp.route('/password', methods=['POST'])
@login_required
def update_password():
    user = current_user()
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirmation = request.form.get('password_confirmation', '')
    if not check_password_hash(user.password_hash, current_password):
        flash('現在のパスワードが正しくありません。', 'error')
    elif len(new_password) < 8:
        flash('新しいパスワードは8文字以上にしてください。', 'error')
    elif new_password != confirmation:
        flash('新しいパスワードが一致しません。', 'error')
    else:
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('パスワードを変更しました。', 'success')
    return redirect(url_for('settings.settings_page'))


def _parse_candidate_deadline(value):
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M') if value else None
    except ValueError:
        return None


@settings_bp.route('/imports')
@admin_required
def imports_page():
    candidates = ImportCandidate.query.order_by(ImportCandidate.created_at.desc()).all()
    return render_template('settings/imports.html', candidates=candidates)


@settings_bp.route('/imports/candidates', methods=['POST'])
@admin_required
def add_import_candidate():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    source_url = request.form.get('source_url', '').strip()
    if not title or not content or not source_url:
        flash('タイトル、内容、出典URLは必須です。', 'error')
    else:
        db.session.add(ImportCandidate(
            source_name=request.form.get('source_name', '秋田県イベントカレンダー').strip() or '秋田県イベントカレンダー',
            source_url=source_url, title=title, content=content,
            place=request.form.get('place', '').strip(),
            deadline=_parse_candidate_deadline(request.form.get('deadline')),
            category=request.form.get('category', 'その他').strip() or 'その他',
        ))
        db.session.commit()
        flash('承認待ちのイベント候補を登録しました。', 'success')
    return redirect(url_for('settings.imports_page'))


@settings_bp.route('/imports/<int:candidate_id>/approve', methods=['POST'])
@admin_required
def approve_import_candidate(candidate_id):
    candidate = db.session.get(ImportCandidate, candidate_id)
    if not candidate or candidate.status != 'pending':
        flash('この候補は承認できません。', 'error')
        return redirect(url_for('settings.imports_page'))
    post = InfoPost(
        tab='event', category=candidate.category, title=candidate.title,
        content=candidate.content, place=candidate.place, deadline=candidate.deadline,
        author_id=current_user().id,
    )
    db.session.add(post)
    db.session.flush()
    candidate.status = 'approved'
    candidate.approved_at = datetime.now()
    candidate.approved_by_id = current_user().id
    candidate.post_id = post.id
    db.session.commit()
    flash('イベントとして公開しました。', 'success')
    return redirect(url_for('settings.imports_page'))


@settings_bp.route('/imports/<int:candidate_id>/reject', methods=['POST'])
@admin_required
def reject_import_candidate(candidate_id):
    candidate = db.session.get(ImportCandidate, candidate_id)
    if candidate and candidate.status == 'pending':
        candidate.status = 'rejected'
        db.session.commit()
        flash('候補を却下しました。', 'success')
    return redirect(url_for('settings.imports_page'))
