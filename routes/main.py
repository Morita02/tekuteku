"""
routes/main.py  ── ホーム・検索・履歴ページ
"""

from datetime import datetime

from flask import Blueprint, render_template, request, session
from extensions import db
from models import InfoPost
from routes.auth import current_user

main_bp = Blueprint('main', __name__)


def _get_history_data():
    history_ids   = session.get('view_history', [])
    history_posts = [
        db.session.get(InfoPost, pid)
        for pid in reversed(history_ids)
        if db.session.get(InfoPost, pid)
    ]
    user = current_user()
    if user:
        my_posts = InfoPost.query.filter_by(author_id=user.id).order_by(InfoPost.date_posted.desc()).all()
    else:
        my_post_ids = session.get('my_posts', [])
        my_posts = [db.session.get(InfoPost, pid) for pid in reversed(my_post_ids) if db.session.get(InfoPost, pid)]
    return history_posts, my_posts


def _get_categories(tab=None):
    query = db.session.query(InfoPost.category).filter(
        InfoPost.category.isnot(None), InfoPost.category != ''
    )
    if tab:
        query = query.filter(InfoPost.tab == tab)
    return sorted({row[0] for row in query.distinct().all()})


def _visible_on_timeline(query):
    """Keep road reports and events without a deadline; hide expired events."""
    return query.filter(
        db.or_(InfoPost.tab.in_(('location', 'event', 'road')), InfoPost.tab.is_(None)),
        db.or_(
            InfoPost.tab.in_(('road', 'location')),
            InfoPost.deadline.is_(None),
            InfoPost.deadline >= datetime.now(),
        )
    )


@main_bp.route('/')
def index():
    q        = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    selected_tab = request.args.get('tab', 'event').strip()
    if selected_tab not in {'location', 'event', 'road'}:
        selected_tab = 'event'

    query = _visible_on_timeline(InfoPost.query)
    if selected_tab == 'event':
        query = query.filter(db.or_(InfoPost.tab == 'event', InfoPost.tab.is_(None)))
    else:
        query = query.filter(InfoPost.tab == selected_tab)
    if q:
        query = query.filter(
            db.or_(
                InfoPost.title.contains(q),
                InfoPost.content.contains(q),
                InfoPost.description.contains(q),
                InfoPost.place.contains(q),
            )
        )
    if category:
        query = query.filter(InfoPost.category == category)
    posts = query.order_by(InfoPost.date_posted.desc()).all()

    popular_query = _visible_on_timeline(InfoPost.query)
    if selected_tab == 'event':
        popular_query = popular_query.filter(db.or_(InfoPost.tab == 'event', InfoPost.tab.is_(None)))
    else:
        popular_query = popular_query.filter(InfoPost.tab == selected_tab)
    popular_posts = popular_query.order_by(InfoPost.likes.desc()).limit(3).all()
    history_posts, my_posts = _get_history_data()
    categories = _get_categories(tab=selected_tab)

    return render_template(
        'index.html',
        posts=posts,
        popular_posts=popular_posts,
        history_posts=history_posts,
        my_posts=my_posts,
        search_query=q,
        category=category,
        categories=categories,
        selected_tab=selected_tab,
    )


@main_bp.route('/search')
def search_page():
    q = request.args.get('q', '').strip()
    categories = _get_categories()
    return render_template('search.html', search_query=q, categories=categories)


@main_bp.route('/history')
def history_page():
    history_posts, my_posts = _get_history_data()
    return render_template('history.html', history_posts=history_posts, my_posts=my_posts)


@main_bp.route('/road')
def road_page():
    q        = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    from models import InfoPost
    query = InfoPost.query.filter_by(tab='road')
    if q:
        query = query.filter(
            db.or_(InfoPost.title.contains(q), InfoPost.content.contains(q), InfoPost.place.contains(q))
        )
    if category:
        query = query.filter(InfoPost.category == category)
    posts = query.order_by(InfoPost.date_posted.desc()).all()
    categories = _get_categories(tab='road')
    return render_template(
        'road.html', posts=posts, search_query=q, category=category, categories=categories
    )
