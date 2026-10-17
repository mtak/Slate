FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SLATE_HOST=0.0.0.0 \
    SLATE_LAYOUT_PATH=/config/layout.json

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
EXPOSE 8000
CMD ["python", "app.py"]
