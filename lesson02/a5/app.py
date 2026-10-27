import datetime
import os
import socket

from flask import Flask

LOG_DIR = "/app/logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
os.makedirs(LOG_DIR, exist_ok=True)

app = Flask(__name__)


def write_log(message):
    # Append one timestamped line; the container ID shows which container wrote it
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} [{socket.gethostname()}] {message}\n")


@app.route("/")
def index():
    write_log("Visit to /")
    return "Visit logged\n"


@app.route("/logs")
def show_logs():
    with open(LOG_FILE) as f:
        return f.read()


if __name__ == "__main__":
    write_log("Container started")
    app.run(host="0.0.0.0", port=5000)
