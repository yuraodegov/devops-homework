import getpass
import socket

from flask import Flask

# Account name of the user running this process inside the container
user = getpass.getuser()
print(f"User name: {user}", flush=True)

app = Flask(__name__)


@app.route("/")
def index():
    return f"Container: {socket.gethostname()}, user: {user}\n"


if __name__ == "__main__":
    # 0.0.0.0 makes the server reachable from outside the container
    app.run(host="0.0.0.0", port=5000)
