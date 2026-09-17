"""
routes/posts.py  ── 投稿・詳細・編集・削除・いいね・リプライ
"""

import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash
from werkzeug.utils import secure_filename
from extensions import db
from models import InfoPost, Location, PostImage, Reply, ReplyImage
from routes.auth import current_user, login_required

posts_bp = Blueprint('posts', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_IMAGES = 5
EVENT_CATEGORIES = ('お祭り・地域行事', '子ども・家族', '音楽・文化', 'スポーツ・健康', '講座・ワークショップ', '募集・ボランティア', 'その他')
ROAD_CATEGORIES = ('通行止め', '渋滞', '工事', '事故', '気象・災害', '公共交通', 'その他')
LOCATION_CATEGORIES = ('お知らせ', '口コミ', '質問', 'おすすめ', '写真', 'その他')


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _save_uploaded_image(file):
    if not file or file.filename == '':
        return None
    if not _allowed_file(file.filename):
        return None
    filename = secure_filename(file.filename)
    filename = datetime.now().strftime('%Y%m%d%H%M%S_') + filename
    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    return filename


def _save_uploaded_images(files):
    saved = []
    for file in files[:MAX_IMAGES]:
        filename = _save_uploaded_image(file)
        if filename:
            saved.append(filename)
    return saved


def _blur_latlng(raw_lat, raw_lng):
    try:
        return round(float(raw_lat), 2), round(float(raw_lng), 2)
    except (TypeError, ValueError):
        return None, None


def _parse_deadline(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except ValueError:
        return None


def _category_for(tab, value):
    choices = {
        'event': EVENT_CATEGORIES,
        'road': ROAD_CATEGORIES,
        'location': LOCATION_CATEGORIES,
    }.get(tab, EVENT_CATEGORIES)
    return value if value in choices else 'その他'


def _is_owner(post):
    user = current_user()
    return (user and post.author_id == user.id) or (not post.author_id and post.id in session.get('my_posts', []))


@posts_bp.route('/post_page')
def post_page():
    location_id = request.args.get('location_id', type=int)
    selected_location = db.session.get(Location, location_id) if location_id else None
    selected_tab = request.args.get('tab', 'event')
    if selected_tab not in {'event', 'road', 'location'}:
        selected_tab = 'event'
    return render_template(
        'post.html', event_categories=EVENT_CATEGORIES, road_categories=ROAD_CATEGORIES,
        location_categories=LOCATION_CATEGORIES,
        locations=Location.query.order_by(Location.name).all(), selected_location=selected_location,
        selected_tab=selected_tab,
    )


@posts_bp.route('/add', methods=['POST'])
@login_required
def add_info():
    if request.form.get('posting_source') != 'post_page':
        flash('投稿は投稿画面から行ってください。', 'error')
        return redirect(url_for('posts.post_page'))
    image_files = _save_uploaded_images(request.files.getlist('images'))
    lat, lng   = _blur_latlng(request.form.get('latitude'), request.form.get('longitude'))
    location_id = request.form.get('location_id', type=int)
    location = db.session.get(Location, location_id) if location_id else None
    tab = request.form.get('tab', 'event')
    if tab == 'location' and not location:
        flash('場所への投稿では、登録済みの場所を選択してください。', 'error')
        return redirect(url_for('posts.post_page'))

    author = current_user()
    new_post = InfoPost(
        tab=tab,
        category=_category_for(tab, request.form.get('category', '')),
        title=request.form.get('title', '無題'),
        content=request.form.get('content', ''),
        description=request.form.get('description', ''),
        place=location.name if location else request.form.get('place', ''),
        latitude=location.lat if location else lat,
        longitude=location.lng if location else lng,
        image_file=image_files[0] if image_files else None,
        deadline=_parse_deadline(request.form.get('deadline')),
        author_id=author.id,
        location_id=location.id if location else None,
    )
    new_post.images = [PostImage(filename=filename, sort_order=index) for index, filename in enumerate(image_files)]
    db.session.add(new_post)
    author.level = max(author.level or 1, 1) + 1
    db.session.commit()

    my_posts = session.get('my_posts', [])
    my_posts.append(new_post.id)
    session['my_posts'] = my_posts
    session.modified = True

    flash(f'投稿しました。レベルが {author.level} に上がりました！', 'success')
    return redirect(url_for('main.index'))


@posts_bp.route('/post/<int:post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    post = db.session.get(InfoPost, post_id)
    if not post:
        return '記事が見つかりません', 404

    if request.method == 'POST':
        if not current_user():
            flash('返信にはログインが必要です。', 'error')
            return redirect(url_for('auth.login', next=request.url))
        content = request.form.get('reply_content', '').strip()
        image_files = _save_uploaded_images(request.files.getlist('reply_images'))
        if content or image_files:
            reply = Reply(post_id=post_id, content=content, author_id=current_user().id)
            reply.images = [ReplyImage(filename=filename, sort_order=index)
                            for index, filename in enumerate(image_files)]
            db.session.add(reply)
            db.session.commit()
        else:
            flash('返信内容または画像を選択してください。', 'error')
        return redirect(url_for('posts.view_post', post_id=post_id))

    history = session.get('view_history', [])
    if post_id in history:
        history.remove(post_id)
    history.append(post_id)
    if len(history) > 5:
        history.pop(0)
    session['view_history'] = history
    session.modified = True

    replies   = Reply.query.filter_by(post_id=post_id).order_by(Reply.date_replied.asc()).all()
    share_url = url_for('posts.view_post', post_id=post_id, _external=True)
    is_mine   = _is_owner(post)
    can_delete = is_mine or bool(current_user() and current_user().is_admin)

    return render_template(
        'post_detail.html', post=post, replies=replies,
        share_url=share_url, is_mine=is_mine, can_delete=can_delete,
    )


@posts_bp.route('/reply/<int:reply_id>/delete', methods=['POST'])
@login_required
def delete_reply(reply_id):
    reply = db.session.get(Reply, reply_id)
    user = current_user()
    if not reply:
        return '返信が見つかりません', 404
    if reply.author_id != user.id and not user.is_admin:
        return '削除権限がありません', 403
    post_id = reply.post_id
    db.session.delete(reply)
    db.session.commit()
    flash('返信を削除しました。', 'success')
    return redirect(url_for('posts.view_post', post_id=post_id))


@posts_bp.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    post = db.session.get(InfoPost, post_id)
    if post:
        post.likes += 1
        db.session.commit()
    return redirect(request.referrer or url_for('main.index'))


@posts_bp.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    post = db.session.get(InfoPost, post_id)
    if not post:
        return '記事が見つかりません', 404
    if not (_is_owner(post) or (current_user() and current_user().is_admin)):
        return '編集権限がありません', 403

    if request.method == 'POST':
        location_id = request.form.get('location_id', type=int)
        location = db.session.get(Location, location_id) if location_id else None
        post.category    = _category_for(post.tab, request.form.get('category', ''))
        post.title       = request.form.get('title', post.title)
        post.content     = request.form.get('content', post.content)
        post.description = request.form.get('description', post.description)
        post.place       = location.name if location else request.form.get('place', post.place)
        post.location_id = location.id if location else None
        if location:
            post.latitude = location.lat
            post.longitude = location.lng
        post.deadline    = _parse_deadline(request.form.get('deadline'))
        image_files = _save_uploaded_images(request.files.getlist('images'))
        if image_files:
            start_order = len(post.images)
            post.images.extend(
                PostImage(filename=filename, sort_order=start_order + index)
                for index, filename in enumerate(image_files)
            )
            if not post.image_file:
                post.image_file = image_files[0]
        db.session.commit()
        return redirect(url_for('posts.view_post', post_id=post_id))

    return render_template(
        'edit.html', post=post, event_categories=EVENT_CATEGORIES, road_categories=ROAD_CATEGORIES,
        location_categories=LOCATION_CATEGORIES,
        locations=Location.query.order_by(Location.name).all(),
    )


@posts_bp.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    post_for_authorization = db.session.get(InfoPost, post_id)
    user = current_user()
    if post_for_authorization and user and (post_for_authorization.author_id == user.id or user.is_admin):
        my_posts = session.get('my_posts', [])
        if post_id not in my_posts:
            my_posts.append(post_id)
            session['my_posts'] = my_posts
    if post_id not in session.get('my_posts', []):
        return '削除権限がありません', 403
    post = db.session.get(InfoPost, post_id)
    if post:
        db.session.delete(post)
        db.session.commit()
        my_posts = session.get('my_posts', [])
        if post_id in my_posts:
            my_posts.remove(post_id)
        session['my_posts'] = my_posts
        session.modified = True
    return redirect(url_for('main.index'))
