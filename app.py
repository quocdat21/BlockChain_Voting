from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Candidate, Poll, init_db
from blockchain import Blockchain
import json

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
    now = datetime.now()

    # Tìm poll đang hoạt động
    poll = Poll.query.filter(Poll.start_time <= now, Poll.end_time >= now).first()
    if not poll:
        flash("Không có cuộc bình chọn nào đang diễn ra!", "danger")
        return render_template("voting.html", voting_open=False)

    candidates = poll.candidates
    has_voted = blockchain.has_voted(username)
    user_vote = blockchain.get_vote_by_user(username)

    if request.method == "POST" and not has_voted:
        candidate_id = request.form.get("candidate")
        candidate = Candidate.query.get(candidate_id)
        if candidate and candidate.poll_id == poll.id:
            blockchain.add_vote(username, candidate.name)
            flash(f"Bạn đã bỏ phiếu cho {candidate.name}!", "success")
            return redirect(url_for("voting"))

    return render_template("voting.html", 
                           candidates=candidates,
                           end_time=poll.end_time.isoformat(),
                           voting_open=True,
                           has_voted=has_voted,
                           user_vote=user_vote)

@app.route("/admin", methods=["GET"])
def admin():
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))
    
    polls = Poll.query.order_by(Poll.start_time.desc()).all()

    # Đếm số phiếu cho mỗi poll
    all_votes = blockchain.get_all_votes()
    for poll in polls:
        count = sum(1 for vote in all_votes if vote.get("candidate") in [c.name for c in poll.candidates])
        poll.vote_count = count

    return render_template("admin.html", polls=polls, now=datetime.now())


@app.route("/admin/create", methods=["POST"])
def create_poll():
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))

    try:
        title = request.form.get("poll_title")
        start_time = datetime.strptime(request.form.get("start_time"), "%Y-%m-%dT%H:%M")
        end_time = datetime.strptime(request.form.get("end_time"), "%Y-%m-%dT%H:%M")
        candidates_json = request.form.get("candidates")
        candidates_list = json.loads(candidates_json)

        new_poll = Poll(title=title, start_time=start_time, end_time=end_time)
        db.session.add(new_poll)
        db.session.commit()

        for c_name in candidates_list:
            db.session.add(Candidate(name=c_name, poll_id=new_poll.id))
        
        db.session.commit()
        flash("Tạo cuộc bình chọn thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi tạo cuộc bình chọn: {str(e)}", "danger")

    return redirect(url_for("admin"))

@app.route("/admin/poll/<int:poll_id>")
def poll_detail(poll_id):
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))

    poll = Poll.query.get_or_404(poll_id)
    votes = blockchain.get_all_votes()

    vote_counts = {c.name: 0 for c in poll.candidates}
    for vote in votes:
        if vote["candidate"] in vote_counts:
            vote_counts[vote["candidate"]] += 1

    return render_template("poll_detail.html", poll=poll, vote_counts=vote_counts, votes=votes)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/blockchain")
def get_blockchain():
    return jsonify(blockchain.chain), 200


if __name__ == "__main__":
    app.run(debug=True)
