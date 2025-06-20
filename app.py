from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import Block, db, User, Candidate, Poll, init_db
from blockchain import Blockchain
import json

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "your_secret_key"

# Khởi tạo database
init_db(app)

# Khởi tạo Blockchain sau khi có app context
blockchain = Blockchain()
with app.app_context():
    blockchain.init_chain_if_needed()


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
            return redirect(url_for("admin" if user.is_admin else "voting_list"))
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

@app.route("/voting/list")
def voting_list():
    if "user_id" not in session or session.get("is_admin"):
        return redirect(url_for("login"))
    now = datetime.now()
    polls = Poll.query.filter(Poll.start_time <= now, Poll.end_time >= now).all()
    return render_template("voting_dashboard.html", polls=polls, username=session.get("username"))

@app.route("/voting/<int:poll_id>", methods=["GET", "POST"])
def voting(poll_id):
    if "user_id" not in session or session.get("is_admin"):
        return redirect(url_for("login"))

    username = session["username"]
    poll = Poll.query.get_or_404(poll_id)
    now = datetime.now()

    if not (poll.start_time <= now <= poll.end_time):
        flash("Cuộc bình chọn này chưa bắt đầu hoặc đã kết thúc.", "danger")
        return redirect(url_for("voting_list"))

    candidates = poll.candidates
    has_voted = blockchain.has_voted(username, poll.id)
    user_vote = blockchain.get_vote_by_user(username, poll.id)

    if request.method == "POST" and not has_voted:
        candidate_id = request.form.get("candidate")
        candidate = Candidate.query.get(candidate_id)
        if candidate and candidate.poll_id == poll.id:
            blockchain.add_vote(username, candidate.name, poll.id)
            flash(f"Bạn đã bỏ phiếu cho {candidate.name}!", "success")
            return redirect(url_for("voting", poll_id=poll.id))

    return render_template("voting.html",
                           poll=poll,
                           candidates=candidates,
                           end_time=poll.end_time.isoformat(),
                           user_vote=user_vote)

@app.route("/admin")
def admin():
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))

    polls = Poll.query.order_by(Poll.start_time.desc()).all()
    all_votes = blockchain.get_all_votes()

    for poll in polls:
        poll.vote_count = sum(1 for vote in all_votes if vote["candidate"] in [c.name for c in poll.candidates])

    return render_template("admin.html", polls=polls, now=datetime.now(), username=session.get("username"))

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
        if vote["poll_id"] == poll.id and vote["candidate"] in vote_counts:
            vote_counts[vote["candidate"]] += 1

    # Lấy các khối liên quan đến cuộc bình chọn
    poll_blocks = []
    blocks = Block.query.order_by(Block.index).all()
    for block in blocks:
        block_votes = [v for v in json.loads(block.votes_json) if v["poll_id"] == poll.id]
        if block_votes:
            poll_blocks.append({
                "index": block.index,
                "timestamp": block.timestamp,
                "votes": block_votes,
                "hash": block.hash,
                "previous_hash": block.previous_hash
            })

    return render_template("poll_detail.html",
                           poll=poll,
                           vote_counts=vote_counts,
                           votes=[v for v in votes if v["poll_id"] == poll.id],
                           blocks=poll_blocks)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/blockchain")
def get_blockchain():
    blocks = Block.query.order_by(Block.index).all()
    chain = []
    for block in blocks:
        chain.append({
            "index": block.index,
            "timestamp": block.timestamp.isoformat(),
            "votes": json.loads(block.votes_json),
            "voted_users": json.loads(block.voted_users_json),
            "previous_hash": block.previous_hash,
            "hash": block.hash
        })
    return jsonify(chain), 200

from flask import jsonify

from flask import jsonify
import json

@app.route("/debug/blocks")
def debug_blocks():
    blocks = Block.query.all()
    result = []
    for b in blocks:
        try:
            votes = json.loads(b.votes_json)
        except Exception as e:
            votes = f"Lỗi giải mã votes_json: {str(e)}"

        try:
            voted_users = json.loads(b.voted_users_json)
        except Exception as e:
            voted_users = f"Lỗi giải mã voted_users_json: {str(e)}"

        result.append({
            "index": b.index,
            "timestamp": b.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "votes": votes,
            "voted_users": voted_users,
            "hash": b.hash,
            "previous_hash": b.previous_hash
        })

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
