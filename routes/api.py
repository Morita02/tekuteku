"""
routes/api.py  ── JSON APIエンドポイント
"""

from flask import Blueprint, jsonify, request
from extensions import db
from models import InfoPost, Location, Reply

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/locations')
def api_locations():
    return jsonify([loc.to_dict() for loc in Location.query.all()])


@api_bp.route('/posts')
def api_posts():
    tab = request.args.get('tab', '').strip()
    q   = request.args.get('q',   '').strip()
    query = InfoPost.query
    if tab:
        query = query.filter_by(tab=tab)
    if q:
        query = query.filter(
            db.or_(
                InfoPost.title.contains(q),
                InfoPost.content.contains(q),
                InfoPost.place.contains(q),
            )
        )
    return jsonify([p.to_dict() for p in query.order_by(InfoPost.date_posted.desc()).all()])


@api_bp.route('/posts/<int:post_id>')
def api_post_detail(post_id):
    post = db.session.get(InfoPost, post_id)
    if not post:
        return jsonify({'error': '記事が見つかりません'}), 404
    replies = Reply.query.filter_by(post_id=post_id).order_by(Reply.date_replied.asc()).all()
    return jsonify({'post': post.to_dict(), 'replies': [r.to_dict() for r in replies]})


@api_bp.route('/popular')
def api_popular():
    tab = request.args.get('tab', '').strip()
    query = InfoPost.query
    if tab:
        query = query.filter_by(tab=tab)
    return jsonify([p.to_dict() for p in query.order_by(InfoPost.likes.desc()).limit(3).all()])
