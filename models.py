from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# Bookモデル（新規）
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)  # 書籍タイトル
    author = db.Column(db.String(200), nullable=True)  # 著者名
    published_date = db.Column(db.Date, nullable=True)  # 出版日
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # ユーザーID
    content = db.Column(db.String(500), nullable=True) 
    yoyaku = db.Column(db.String(500), nullable=True) 
    vector = db.Column(db.JSON, default={}, nullable=True) 

    # ユーザーと関連付け
    user = db.relationship('User', backref=db.backref('books', lazy=True))

# 中間テーブル
user_books = db.Table('user_books',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    profile_image = db.Column(db.String(300), default="default.jpg")
    data = db.Column(db.JSON, default={})  # Additional user data in JSON format
    
    visibility = db.Column(db.JSON, nullable=True)

    type = db.Column(db.String(150))
 # 多対多リレーション
    read_books = db.relationship('Book', secondary=user_books, backref=db.backref('read_by', lazy='dynamic'))

 # 自分メモとのリレーション
    notes = db.relationship('UserNote', backref='user', lazy=True)


    def __repr__(self):
        return f'<User {self.username}>'
    

# 中間テーブル（コラムと書籍の多対多関係）
column_books = db.Table(
    'column_books',
    db.Column('column_id', db.Integer, db.ForeignKey('column.id'), primary_key=True),
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True)
)

# Columnモデル
class Column(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # コラムのタイトル
    content = db.Column(db.Text, nullable=False)       # コラムの本文
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 作成日時

    # ユーザーとの関連
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('columns', lazy=True))

    # 書籍との多対多リレーション
    books = db.relationship('Book', secondary=column_books, backref=db.backref('columns', lazy='dynamic'))


# 中間テーブル（プラン利用者とプラン）
plan_users = db.Table('plan_users',
    db.Column('plan_id', db.Integer, db.ForeignKey('plans.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

# 中間テーブル（プランに含まれる本とプラン）
plan_books = db.Table('plan_books',
    db.Column('plan_id', db.Integer, db.ForeignKey('plans.id'), primary_key=True),
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True)
)


class Plan(db.Model):
    __tablename__ = 'plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # プラン名
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 作成日時
    data = db.Column(db.JSON, default={})
    # プラン作成者
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.relationship('User', backref=db.backref('created_plans', lazy=True))

    # 利用者（多対多リレーション）
    users = db.relationship('User', secondary=plan_users, backref=db.backref('plans', lazy=True))

    # 含まれる本（多対多リレーション）
    books = db.relationship('Book', secondary=plan_books, backref=db.backref('plans', lazy=True))

    def __repr__(self):
        return f'<Plan {self.name}>'
    

# 自分メモモデル
class UserNote(db.Model):
    __tablename__ = 'user_notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # ユーザーID
    source_type = db.Column(db.Enum('book', 'column', 'custom', 'persona','plan', name='source_type_enum'), nullable=False)  # メモの元
    source_id = db.Column(db.Integer, nullable=True)  # 書籍やコラムのID
    highlight_text = db.Column(db.Text, nullable=True)  # ハイライトされたテキスト
    custom_text = db.Column(db.Text, nullable=True)  # ユーザーの自由記述
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 作成日時
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新日時
    memo_type =  db.Column(db.Text, nullable=True) 

    def __repr__(self):
        return f'<UserNote {self.source_type} - {self.id}>'