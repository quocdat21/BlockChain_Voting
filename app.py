from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Candidate, VotingConfig, init_db
from blockchain import Blockchain
from flask import jsonify

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "your_secret_key"
init_db(app)

blockchain = Blockchain()

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.clear()
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["is_admin"] = user.is_admin
            return redirect(url_for("admin" if user.is_admin else "voting"))
        flash("Sai tài khoản hoặc mật khẩu!", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        if User.query.filter_by(username=username).first():
            flash("Tài khoản đã tồn tại!", "danger")
        else:
            new_user = User(username=username, password=password, is_admin=False)
            db.session.add(new_user)
            db.session.commit()
            flash("Đăng ký thành công! Hãy đăng nhập.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/voting", methods=["GET", "POST"])
def voting():
    if "user_id" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    config = VotingConfig.query.first()
    current_time = datetime.now()

    if not config or current_time < config.start_time or current_time > config.end_time:
        flash("Bình chọn hiện không hoạt động!", "danger")
        return redirect(url_for("voting"))

    candidates = Candidate.query.all()
    has_voted = blockchain.has_voted(username)

    if request.method == "POST" and not has_voted:
        candidate_id = request.form.get("candidate")
        candidate = Candidate.query.get(candidate_id)
        if candidate:
            blockchain.add_vote(username, candidate.name)
            flash(f"Bạn đã bỏ phiếu cho {candidate.name}!", "success")
            return redirect(url_for("voting"))

    return render_template("voting.html", 
                           candidates=candidates, 
                           end_time=config.end_time.isoformat(),
                           has_voted=has_voted)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))

    if request.method == "POST":
        if "candidate_name" in request.form:
            new_candidate = Candidate(name=request.form["candidate_name"])
            db.session.add(new_candidate)
            db.session.commit()
        elif "start_time" in request.form and "end_time" in request.form:
            start_time = datetime.strptime(request.form["start_time"], "%Y-%m-%dT%H:%M")
            end_time = datetime.strptime(request.form["end_time"], "%Y-%m-%dT%H:%M")
            config = VotingConfig.query.first()
            if config:
                config.start_time = start_time
                config.end_time = end_time
            else:
                db.session.add(VotingConfig(start_time=start_time, end_time=end_time))
            db.session.commit()

    votes = blockchain.get_all_votes()
    candidates = Candidate.query.all()
    config = VotingConfig.query.first()

    vote_counts = {candidate.name: 0 for candidate in candidates}
    for vote in votes:
        vote_counts[vote["candidate"]] += 1

    return render_template("admin.html", 
                           votes=votes, 
                           candidates=candidates, 
                           config=config, 
                           vote_counts=vote_counts, 
                           now=datetime.now())

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/blockchain")
def get_blockchain():
    return jsonify(blockchain.chain), 200

if __name__ == "__main__":
    app.run(debug=True)
