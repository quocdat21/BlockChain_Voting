import hashlib
import json
from datetime import datetime
from models import db, Block


class Blockchain:
    def __init__(self):
        self.current_votes = {}
        self.voted_users = {}

    def init_chain_if_needed(self, poll_id):
        """Tạo genesis block nếu poll chưa có block nào."""
        if not Block.query.filter_by(poll_id=poll_id).first():
            self.create_genesis_block(poll_id)

    def create_genesis_block(self, poll_id):
        genesis_block = Block(
            poll_id=poll_id,
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

    def create_block(self, poll_id, previous_hash):
        if poll_id not in self.current_votes or not self.current_votes[poll_id]:
            return None

        last_block = Block.query.filter_by(poll_id=poll_id).order_by(Block.index.desc()).first()
        new_index = last_block.index + 1 if last_block else 1

        votes = self.current_votes[poll_id]
        voted_users = self.voted_users.get(poll_id, {})

        new_block = Block(
            poll_id=poll_id,
            index=new_index,
            timestamp=datetime.utcnow(),
            votes_json=json.dumps(votes),
            voted_users_json=json.dumps(voted_users),
            previous_hash=previous_hash,
            hash=self.hash_block(new_index, votes, voted_users, previous_hash)
        )

        db.session.add(new_block)
        db.session.commit()

        # Reset dữ liệu tạm cho poll này
        self.current_votes[poll_id] = []
        self.voted_users[poll_id] = {}
        return new_block

    def add_vote(self, voter, candidate, poll_id):
        self.init_chain_if_needed(poll_id)

        if self.has_voted(voter, poll_id):
            return False

        vote = {
            "voter": voter,
            "candidate": candidate,
            "poll_id": poll_id
        }

        if poll_id not in self.current_votes:
            self.current_votes[poll_id] = []
        self.current_votes[poll_id].append(vote)

        if poll_id not in self.voted_users:
            self.voted_users[poll_id] = {}
        self.voted_users[poll_id][voter] = candidate

        last_block = Block.query.filter_by(poll_id=poll_id).order_by(Block.index.desc()).first()
        previous_hash = last_block.hash if last_block else "0"
        self.create_block(poll_id, previous_hash)
        return True

    def has_voted(self, voter, poll_id):
        blocks = Block.query.filter_by(poll_id=poll_id).all()
        for block in blocks:
            voted_dict = json.loads(block.voted_users_json)
            if voter in voted_dict:
                return True
        return voter in self.voted_users.get(poll_id, {})

    def get_vote_by_user(self, voter, poll_id):
        blocks = Block.query.filter_by(poll_id=poll_id).all()
        for block in blocks:
            votes = json.loads(block.votes_json)
            for vote in votes:
                if vote["voter"] == voter:
                    return vote["voter"], vote["candidate"]

        for vote in self.current_votes.get(poll_id, []):
            if vote["voter"] == voter:
                return vote["voter"], vote["candidate"]

        return None

    def get_all_votes(self):
        votes = []
        all_blocks = Block.query.all()
        for block in all_blocks:
            votes.extend(json.loads(block.votes_json))

        # Thêm cả các votes đang chờ trong self.current_votes
        for poll_votes in self.current_votes.values():
            votes.extend(poll_votes)

        return votes
