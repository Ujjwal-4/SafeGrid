FROM python:3.11-slim
WORKDIR /app

COPY src/platform/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/platform/ .

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["python", "-u", "app.py"]
