import hashlib
import json
from time import time

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_votes = []
        self.voted_users = {}  # Thay vì set, dùng dict để lưu cả ứng viên đã chọn
        self.create_genesis_block()

    def create_genesis_block(self):
        """Tạo khối đầu tiên (Genesis block)."""
        genesis_block = {
            "index": 1,
            "timestamp": time(),
            "votes": [],
            "voted_users": {},
            "previous_hash": "0"
        }
        genesis_block["hash"] = self.hash(genesis_block)
        self.chain.append(genesis_block)

    def create_block(self, previous_hash):
        """Tạo block mới chứa các phiếu bầu."""
        if not self.current_votes:
            return None

        block = {
            "index": len(self.chain) + 1,
            "timestamp": time(),
            "votes": self.current_votes.copy(),
            "voted_users": self.voted_users.copy(),
            "previous_hash": previous_hash
        }
        block["hash"] = self.hash(block)

        self.chain.append(block)
        self.current_votes = []
        self.voted_users.clear()

        return block

    def add_vote(self, voter, candidate):
        """Thêm một phiếu bầu (nếu chưa vote)."""
        if self.has_voted(voter):
            return False

        self.current_votes.append({"voter": voter, "candidate": candidate})
        self.voted_users[voter] = candidate

        previous_hash = self.chain[-1]["hash"] if self.chain else "0"
        self.create_block(previous_hash)
        return True

    def has_voted(self, voter):
        """Kiểm tra xem người dùng đã bỏ phiếu chưa (cả trong block và vote chờ)."""
        # Kiểm tra trong block
        for block in self.chain:
            if voter in block.get("voted_users", {}):
                return True
        # Kiểm tra trong vote chờ
        return voter in self.voted_users

    def get_vote_by_user(self, voter):
        """Trả về phiếu bầu của người dùng (nếu có)."""
        for block in self.chain:
            for vote in block["votes"]:
                if vote["voter"] == voter:
                    return vote["voter"], vote["candidate"]
        for vote in self.current_votes:
            if vote["voter"] == voter:
                return vote["voter"], vote["candidate"]
        return None

    def get_all_votes(self):
        """Lấy tất cả phiếu bầu từ blockchain."""
        votes = []
        for block in self.chain:
            votes.extend(block["votes"])
        votes.extend(self.current_votes)
        return votes

    @staticmethod
    def hash(block):
        """Tạo hash SHA-256 cho block."""
        # Loại bỏ key 'hash' ra khỏi bản sao của block trước khi hash chính nó
        block_copy = dict(block)
        block_copy.pop("hash", None)
        return hashlib.sha256(json.dumps(block_copy, sort_keys=True).encode()).hexdigest()
