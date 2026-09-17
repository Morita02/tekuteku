"""
models.py
─────────
SQLAlchemyモデル定義。
db は extensions.py からインポートする（app.py からではない）。
"""

from datetime import datetime
from extensions import db


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    display_name = db.Column(db.String(50))
    level = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    posts = db.relationship('InfoPost', backref='author', lazy=True)
    replies = db.relationship('Reply', backref='author', lazy=True)


class ImportCandidate(db.Model):
    __tablename__ = 'import_candidate'

    id = db.Column(db.Integer, primary_key=True)
    source_name = db.Column(db.String(100), nullable=False)
    source_url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    place = db.Column(db.String(100))
    deadline = db.Column(db.DateTime)
    category = db.Column(db.String(50), default='その他')
    status = db.Column(db.String(20), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    approved_at = db.Column(db.DateTime)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('info_post.id'))


# ──────────────────────────────────────────────
# 投稿モデル
# ──────────────────────────────────────────────
class InfoPost(db.Model):
    __tablename__ = 'info_post'

    id           = db.Column(db.Integer, primary_key=True)
    tab          = db.Column(db.String(20), default='event')
    category     = db.Column(db.String(50))
    title        = db.Column(db.String(200), nullable=False)
    content      = db.Column(db.Text, nullable=False)
    description  = db.Column(db.Text)
    place        = db.Column(db.String(100))
    latitude     = db.Column(db.Float)
    longitude    = db.Column(db.Float)
    image_file   = db.Column(db.String(200))
    date_posted  = db.Column(db.DateTime, default=datetime.now)
    likes        = db.Column(db.Integer, default=0)
    deadline     = db.Column(db.DateTime)
    author_id    = db.Column(db.Integer, db.ForeignKey('user.id'))
    location_id  = db.Column(db.Integer, db.ForeignKey('location.id'))

    location = db.relationship('Location', backref='posts')

    replies = db.relationship(
        'Reply', backref='post', lazy=True, cascade='all, delete-orphan'
    )
    images = db.relationship(
        'PostImage', backref='post', lazy=True, cascade='all, delete-orphan',
        order_by='PostImage.sort_order'
    )

    @property
    def image_files(self):
        files = [self.image_file] if self.image_file else []
        files.extend(image.filename for image in self.images if image.filename not in files)
        return files

    def to_dict(self):
        return {
            'id':          self.id,
            'tab':         self.tab,
            'category':    self.category or '',
            'title':       self.title,
            'content':     self.content,
            'description': self.description or '',
            'place':       self.place or '',
            'latitude':    self.latitude,
            'longitude':   self.longitude,
            'image_file':  self.image_file or '',
            'images':      self.image_files,
            'date_posted': self.date_posted.strftime('%Y-%m-%d %H:%M') if self.date_posted else '',
            'likes':       self.likes,
            'deadline':    self.deadline.strftime('%Y-%m-%d %H:%M') if self.deadline else '',
            'author':      self.author.email if self.author else '',
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else '',
            'reply_count': len(self.replies),
        }


class PostImage(db.Model):
    __tablename__ = 'post_image'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('info_post.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)


# ──────────────────────────────────────────────
# 場所モデル（地図マーカー用）
# ──────────────────────────────────────────────
class Location(db.Model):
    __tablename__ = 'location'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    type        = db.Column(db.String(50))
    lat         = db.Column(db.Float, nullable=False)
    lng         = db.Column(db.Float, nullable=False)
    city        = db.Column(db.String(100))
    description = db.Column(db.Text)
    icon_color  = db.Column(db.String(20))   # カスタム色 例: "#e63946"
    icon_file   = db.Column(db.String(200))  # アップロードしたアイコン画像ファイル名
    # 自分で登録した場所だけを編集できるよう、作成者を記録する。
    author_id   = db.Column(db.Integer, db.ForeignKey('user.id'))

    def to_dict(self):
        return {
            'id':          self.id,
            'name':        self.name,
            'type':        self.type or '',
            'lat':         self.lat,
            'lng':         self.lng,
            'city':        self.city or '',
            'description': self.description or '',
            'icon_color':  self.icon_color or '',
            'icon_file':   self.icon_file  or '',
            'author_id':   self.author_id,
        }


# ──────────────────────────────────────────────
# リプライモデル
# ──────────────────────────────────────────────
class Reply(db.Model):
    __tablename__ = 'reply'

    id           = db.Column(db.Integer, primary_key=True)
    post_id      = db.Column(db.Integer, db.ForeignKey('info_post.id'), nullable=False)
    content      = db.Column(db.Text, nullable=False)
    date_replied = db.Column(db.DateTime, default=datetime.now)
    author_id    = db.Column(db.Integer, db.ForeignKey('user.id'))

    images = db.relationship(
        'ReplyImage', backref='reply', lazy=True, cascade='all, delete-orphan',
        order_by='ReplyImage.sort_order'
    )

    def to_dict(self):
        return {
            'id':           self.id,
            'post_id':      self.post_id,
            'content':      self.content,
            'date_replied': self.date_replied.strftime('%Y-%m-%d %H:%M') if self.date_replied else '',
            'author':       self.author.email if self.author else '',
            'images':       [image.filename for image in self.images],
        }


class ReplyImage(db.Model):
    __tablename__ = 'reply_image'

    id = db.Column(db.Integer, primary_key=True)
    reply_id = db.Column(db.Integer, db.ForeignKey('reply.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
