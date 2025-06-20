import hashlib
import json
from datetime import datetime
from models import db, Block


class Blockchain:
    def __init__(self):
        self.current_votes = []
        self.voted_users = {}

    def init_chain_if_needed(self):
        """Chỉ tạo khối Genesis nếu blockchain chưa có dữ liệu."""
        if not Block.query.first():
            self.create_genesis_block()

    def create_genesis_block(self):
        """Tạo khối đầu tiên (genesis)."""
        genesis_block = Block(
            index=1,
            timestamp=datetime.utcnow(),
            votes_json=json.dumps([]),
            voted_users_json=json.dumps({}),
            previous_hash="0",
            hash=self.hash_block(1, [], {}, "0")
        )
        db.session.add(genesis_block)
        db.session.commit()

    def hash_block(self, index, votes, voted_users, previous_hash):
        block_data = {
            "index": index,
            "votes": votes,
            "voted_users": voted_users,
            "previous_hash": previous_hash
        }
        return hashlib.sha256(json.dumps(block_data, sort_keys=True).encode()).hexdigest()

    def create_block(self, previous_hash):
        if not self.current_votes:
            return None

        last_block = Block.query.order_by(Block.index.desc()).first()
        new_index = last_block.index + 1

        new_block = Block(
            index=new_index,
            timestamp=datetime.utcnow(),
            votes_json=json.dumps(self.current_votes),
            voted_users_json=json.dumps(self.voted_users),
            previous_hash=previous_hash,
            hash=self.hash_block(new_index, self.current_votes, self.voted_users, previous_hash)
        )

        db.session.add(new_block)
        db.session.commit()

        self.current_votes = []
        self.voted_users = {}
        return new_block

    def add_vote(self, voter, candidate, poll_id):
        if self.has_voted(voter, poll_id):
            return False

        vote = {
            "voter": voter,
            "candidate": candidate,
            "poll_id": poll_id
        }
        self.current_votes.append(vote)

        poll_id_str = str(poll_id)
        if poll_id_str not in self.voted_users:
            self.voted_users[poll_id_str] = {}
        self.voted_users[poll_id_str][voter] = candidate

        last_block = Block.query.order_by(Block.index.desc()).first()
        previous_hash = last_block.hash if last_block else "0"
        self.create_block(previous_hash)
        return True

    def has_voted(self, voter, poll_id):
        poll_id_str = str(poll_id)
        all_blocks = Block.query.all()
        for block in all_blocks:
            voted_dict = json.loads(block.voted_users_json).get(poll_id_str, {})
            if voter in voted_dict:
                return True
        return poll_id_str in self.voted_users and voter in self.voted_users[poll_id_str]

    def get_vote_by_user(self, voter, poll_id):
        poll_id_str = str(poll_id)
        all_blocks = Block.query.all()
        for block in all_blocks:
            votes = json.loads(block.votes_json)
            for vote in votes:
                if vote["voter"] == voter and str(vote["poll_id"]) == poll_id_str:
                    return vote["voter"], vote["candidate"]
        for vote in self.current_votes:
            if vote["voter"] == voter and str(vote["poll_id"]) == poll_id_str:
                return vote["voter"], vote["candidate"]
        return None

    def get_all_votes(self):
        votes = []
        all_blocks = Block.query.all()
        for block in all_blocks:
            votes.extend(json.loads(block.votes_json))
        votes.extend(self.current_votes)
        return votes
    def init_chain_if_needed(self):
        if not Block.query.first():
            self.create_genesis_block()
