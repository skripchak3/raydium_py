FROM python:3.13.1-alpine3.21

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt && pip install -U solders

COPY bot bot
WORKDIR /app/bot

ENTRYPOINT ["python", "./new.py"]