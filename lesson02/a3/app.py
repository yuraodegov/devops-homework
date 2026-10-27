import os

import redis
from flask import Flask

app = Flask(__name__)

# "redis" is the service name from docker-compose.yml;
# Compose's internal DNS resolves it to the Redis container
cache = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=6379)


@app.route("/")
def index():
    count = cache.incr("hits")
    return f"Hello from Flask! This page has been visited {count} times.\n"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
