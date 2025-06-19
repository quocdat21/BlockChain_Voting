from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    candidates = db.relationship("Candidate", backref="poll", lazy=True, cascade="all, delete")

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'), nullable=False)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        # Tạo admin mặc định nếu chưa có
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password=generate_password_hash("123456"), is_admin=True)
            db.session.add(admin)
            db.session.commit()
