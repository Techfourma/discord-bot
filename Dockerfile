FROM python:3.11.9-slim

WORKDIR /app

COPY config/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run.py"]s