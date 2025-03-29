import hashlib
import json
from time import time

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_votes = []
        self.voted_users = set()
        
        # 🔥 Đảm bảo có Genesis Block khi khởi tạo
        self.create_genesis_block()

    def create_genesis_block(self):
        """Tạo khối khởi đầu cho blockchain"""
        genesis_block = {
            "index": 1,
            "timestamp": time(),
            "votes": [],
            "voted_users": [],
            "previous_hash": "0"
        }
        genesis_block["hash"] = self.hash(genesis_block)
        self.chain.append(genesis_block)

    def create_block(self, previous_hash):
        """Tạo một block mới trong blockchain nếu có phiếu bầu."""
        if not self.current_votes:
            return None  # Không có phiếu thì không tạo block

        block = {
            "index": len(self.chain) + 1,
            "timestamp": time(),
            "votes": self.current_votes.copy(),
            "voted_users": list(self.voted_users),
            "previous_hash": previous_hash
        }
        block["hash"] = self.hash(block)

        self.chain.append(block)
        self.current_votes = []
        self.voted_users.clear()  # Reset danh sách đã bỏ phiếu sau khi lưu block

    def add_vote(self, voter, candidate):
        """Thêm một phiếu bầu và tạo block ngay lập tức."""
        if self.has_voted(voter):
            return False  # Ngăn người dùng bỏ phiếu nhiều lần

        self.current_votes.append({"voter": voter, "candidate": candidate})
        self.voted_users.add(voter)

        # 🔥 Đảm bảo lấy hash của block trước đó an toàn
        previous_hash = self.chain[-1]["hash"] if self.chain else "0"
        self.create_block(previous_hash=previous_hash)
    
        return True

    def get_all_votes(self):
        """Lấy tất cả phiếu bầu từ các block và phiếu hiện tại chưa tạo block."""
        votes = []
        for block in self.chain:
            votes.extend(block["votes"])
        
        # 🔥 Đảm bảo hiển thị cả phiếu chưa lưu vào block
        votes.extend(self.current_votes)
        return votes

    def has_voted(self, voter):
        """Kiểm tra xem người dùng đã bỏ phiếu chưa."""
        return voter in self.voted_users

    @staticmethod
    def hash(block):
        """Tạo mã băm SHA-256 cho block."""
        return hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()
