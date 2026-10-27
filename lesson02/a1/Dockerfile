FROM python:3.9-slim

WORKDIR /app

# Install Flask (no pip cache to keep the image smaller)
RUN pip install --no-cache-dir flask

COPY getUser.py .

# Document the port the app listens on
EXPOSE 5000

CMD ["python", "getUser.py"]
