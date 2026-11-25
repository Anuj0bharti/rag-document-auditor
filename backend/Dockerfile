FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements.txt -r requirements-ml.txt
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
RUN mkdir -p /app/uploads
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
