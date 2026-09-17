"""
routes/map.py  ── 地図ページ・場所登録
"""

import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
import requests as http_requests
from extensions import db
from models import InfoPost, Location
from routes.auth import current_user

map_bp = Blueprint('map', __name__)

ALLOWED_ICON_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}


def _allowed_icon(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_ICON_EXTENSIONS


def _get_city_from_latlng(lat, lng):
    try:
        resp = http_requests.get(
            'https://nominatim.openstreetmap.org/reverse',
            params={'format': 'json', 'lat': lat, 'lon': lng, 'zoom': 10, 'addressdetails': 1},
            headers={'User-Agent': 'tekuteku-akitainu'},
            timeout=8,
        )
        addr = resp.json().get('address', {})
        return (addr.get('city') or addr.get('town') or
                addr.get('village') or addr.get('county') or '不明')
    except Exception:
        return '不明'


def _current_location_editor(location=None):
    """場所の作成・編集を許可されたユーザーを返す。"""
    user = current_user()
    if not user:
        return None, (jsonify({'error': '場所を登録・編集するにはログインが必要です'}), 401)
    if location and location.author_id != user.id and not user.is_admin:
        return None, (jsonify({'error': '自分で登録した場所のみ編集できます'}), 403)
    return user, None


def _save_icon_file(file):
    if not (file and file.filename):
        return None
    if not _allowed_icon(file.filename):
        raise ValueError('PNG、JPG、GIF、SVG、WebP の画像を選択してください')
    filename = 'loc_icon_' + datetime.now().strftime('%Y%m%d%H%M%S_') + secure_filename(file.filename)
    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    return filename


def _remove_icon_file(filename):
    if not filename:
        return
    try:
        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    except OSError:
        pass


@map_bp.route('/map')
def map_page():
    return render_template('map.html')


@map_bp.route('/add_location', methods=['POST'])
def add_location():
    user, error = _current_location_editor()
    if error:
        return error
    try:
        lat = float(request.form['lat'])
        lng = float(request.form['lng'])
    except (KeyError, ValueError):
        return jsonify({'error': '緯度経度が不正です'}), 400

    city = _get_city_from_latlng(lat, lng)

    # アイコン画像のアップロード処理
    try:
        icon_file = _save_icon_file(request.files.get('icon_image'))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    new_loc = Location(
        name=request.form.get('name', ''),
        type=request.form.get('type', 'その他'),
        lat=lat, lng=lng, city=city,
        description=request.form.get('description', ''),
        icon_color=request.form.get('icon_color', '') or None,
        icon_file=icon_file,
        author_id=user.id,
    )
    db.session.add(new_loc)
    db.session.commit()
    return jsonify(new_loc.to_dict())


@map_bp.route('/delete_location/<int:location_id>', methods=['POST'])
def delete_location(location_id):
    loc = db.session.get(Location, location_id)
    if not loc:
        return jsonify({'error': '場所が見つかりません'}), 404
    _, error = _current_location_editor(loc)
    if error:
        return error

    # アップロード済みのアイコン画像があれば一緒に削除
    _remove_icon_file(loc.icon_file)

    InfoPost.query.filter_by(location_id=location_id).update({InfoPost.location_id: None})
    db.session.delete(loc)
    db.session.commit()
    return jsonify({'success': True, 'id': location_id})


@map_bp.route('/update_location_color/<int:location_id>', methods=['POST'])
def update_location_color(location_id):
    loc = db.session.get(Location, location_id)
    if not loc:
        return jsonify({'error': '場所が見つかりません'}), 404
    _, error = _current_location_editor(loc)
    if error:
        return error

    color = request.form.get('icon_color', '').strip()
    if not color:
        return jsonify({'error': '色を指定してください'}), 400

    old_icon_file = loc.icon_file
    loc.icon_color = color
    loc.icon_file  = None  # 色指定に切り替えたらアップロード画像アイコンは解除
    _remove_icon_file(old_icon_file)
    db.session.commit()
    return jsonify(loc.to_dict())


@map_bp.route('/update_location/<int:location_id>', methods=['POST'])
def update_location(location_id):
    loc = db.session.get(Location, location_id)
    if not loc:
        return jsonify({'error': '場所が見つかりません'}), 404
    _, error = _current_location_editor(loc)
    if error:
        return error

    name = request.form.get('name', '').strip()
    location_type = request.form.get('type', '').strip()
    if not name or not location_type:
        return jsonify({'error': '建物名と種類を入力してください'}), 400

    try:
        lat = float(request.form.get('lat', loc.lat))
        lng = float(request.form.get('lng', loc.lng))
    except ValueError:
        return jsonify({'error': '緯度経度が不正です'}), 400

    moved = lat != loc.lat or lng != loc.lng
    loc.name = name
    loc.type = location_type
    loc.description = request.form.get('description', '').strip()
    loc.lat, loc.lng = lat, lng
    if moved:
        loc.city = _get_city_from_latlng(lat, lng)

    icon_mode = request.form.get('icon_mode', '')
    old_icon_file = loc.icon_file
    try:
        new_icon_file = _save_icon_file(request.files.get('icon_image'))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    if new_icon_file:
        loc.icon_file = new_icon_file
        loc.icon_color = None
        _remove_icon_file(old_icon_file)
    elif icon_mode == 'color':
        color = request.form.get('icon_color', '').strip()
        if not color:
            return jsonify({'error': 'アイコンの色を指定してください'}), 400
        loc.icon_color = color
        loc.icon_file = None
        _remove_icon_file(old_icon_file)

    db.session.commit()
    return jsonify(loc.to_dict())
