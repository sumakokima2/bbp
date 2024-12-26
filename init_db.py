# init_db.py の例
from app import app
from models import db, User

with app.app_context():
    db.create_all()  # データベーステーブルを作成
    admin_user = User(username="admin", email="admin@example.com", password="password", is_admin=True)
    db.session.add(admin_user)
    db.session.commit()
    print("Admin user created.")
