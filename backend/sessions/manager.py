import uuid
from datetime import datetime


class SessionManager:

    def __init__(self):
        self.sessions = {}

    def create_session(self):

        session_id = str(uuid.uuid4())

        self.sessions[session_id] = {
            "session_id": session_id,
            "status": "active",
            "created_at": datetime.utcnow().isoformat()
        }

        return self.sessions[session_id]

    def get_session(self, session_id):

        return self.sessions.get(session_id)

    def close_session(self, session_id):

        if session_id in self.sessions:

            self.sessions[session_id]["status"] = "closed"

            return True

        return False