FROM python:3.13.1-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY bot/raydium_py raydium_py
COPY bot bot
WORKDIR /app/bot
RUN pip install -U solders

ENTRYPOINT ["python", "./new.py"]