import os

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

import chatbot

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
socketio = SocketIO(app)

# Per-session conversation history: {session_id: history_ids tensor}
_sessions = {}


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("message")
def handle_message(data):
    user_text = (data.get("text") or "").strip()
    if not user_text:
        return

    sid = request.sid
    history = _sessions.get(sid)

    reply, updated_history = chatbot.respond(user_text, history)
    _sessions[sid] = updated_history

    emit("bot_message", {"text": reply})


@socketio.on("reset")
def handle_reset():
    _sessions.pop(request.sid, None)
    emit("bot_message", {"text": "Conversation cleared."})


@socketio.on("disconnect")
def handle_disconnect():
    _sessions.pop(request.sid, None)


if __name__ == "__main__":
    socketio.run(app, debug=True)
