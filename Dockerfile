FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirenments.txt /app/requirenments.txt
RUN pip install --no-cache-dir -r /app/requirenments.txt

COPY analyzer /app/analyzer
COPY static /app/static
COPY main.py /app/main.py

EXPOSE 8000
# Many hosts set PORT at runtime (Render, Railway, Fly, Cloud Run).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
