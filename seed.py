from flask import Flask, render_template, redirect, url_for, request, flash,  jsonify
from app import db
from models import User, Book, Column, user_books

# データベースを初期化
#db.drop_all()
#db.create_all()


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'



# Flaskアプリケーションコンテキストの設定
with app.app_context():

    # ユーザーのシードデータ
    new_users = [
        User(username="Alice", email="alice@example.com", password="password1"),
        User(username="Bob", email="bob@example.com", password="password2"),
        User(username="Charlie", email="charlie@example.com", password="password3")
    ]

    # 書籍のシードデータ
    books = [
        Book(title="Flask入門", author="山田太郎", published_date="2023-01-01",
            user_id=1),
        Book(title="Pythonプログラミング", author="佐藤花子", published_date="2022-12-15",
            user_id=2),
        Book(title="データベース設計", author="鈴木次郎", published_date="2023-03-10",
            user_id=1),
        Book(title="Webアプリ開発", author="高橋健", published_date="2023-07-21",
            user_id=2)
    ]

    # ユーザーと書籍の読書履歴（user_books中間テーブル）のシードデータ
    read_books_data = [
        {"user_id": 1, "book_id": 1},
        {"user_id": 1, "book_id": 2},
        {"user_id": 2, "book_id": 2},
        {"user_id": 2, "book_id": 3},
        {"user_id": 3, "book_id": 1},
        {"user_id": 3, "book_id": 4}
    ]

    # コラムのシードデータ
    columns = [
        {
            "title": "Flask入門とPythonプログラミングの比較",
            "content": "FlaskとPythonプログラミングを比較して学んだことをまとめました。",
            "user_id": 1,
            "book_ids": [1, 2]
        },
        {
            "title": "データベース設計の基本",
            "content": "データベース設計の重要なポイントを解説します。",
            "user_id": 2,
            "book_ids": [2, 3]
        },
        {
            "title": "Webアプリ開発におけるフレームワークの活用",
            "content": "Webアプリ開発で使用したフレームワークの利点をまとめました。",
            "user_id": 3,
            "book_ids": [1, 4]
        }
    ]

    # データベースに挿入
    try:
        # ユーザーを挿入
        db.session.add_all(new_users)
        db.session.commit()

        # 書籍を挿入
        db.session.add_all(books)
        db.session.commit()

        # 読書履歴を挿入
        for data in read_books_data:
            user = User.query.get(data["user_id"])
            book = Book.query.get(data["book_id"])
            user.read_books.append(book)
        db.session.commit()

        # コラムを挿入
        for column_data in columns:
            user = User.query.get(column_data["user_id"])
            related_books = Book.query.filter(Book.id.in_(column_data["book_ids"])).all()

            new_column = Column(
                title=column_data["title"],
                content=column_data["content"],
                user_id=column_data["user_id"]
            )
            # コラムに関連付ける書籍を設定
            new_column.books.extend(related_books)

            db.session.add(new_column)
        db.session.commit()

        print("シードデータの挿入が完了しました！")

    except Exception as e:
        db.session.rollback()
        print(f"エラーが発生しました: {e}")
