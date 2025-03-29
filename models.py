from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

class VotingConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

def init_db(app):
    with app.app_context():
        db.init_app(app)
        db.create_all()
        # Thêm admin mặc định nếu chưa có
        if not User.query.filter_by(username="admin").first():
            from werkzeug.security import generate_password_hash
            admin = User(username="admin", password=generate_password_hash("123456"), is_admin=True)
            db.session.add(admin)
            db.session.commit()
