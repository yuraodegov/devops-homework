# ---------- Stage 1: builder - install dependencies ----------
FROM python:3.9-slim AS builder

WORKDIR /app
COPY requirements.txt .

# Install packages into an isolated virtual environment
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: runtime - minimal final image ----------
FROM python:3.9-slim

WORKDIR /app

# Take only the ready virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
