FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY web ./web

RUN useradd --create-home bot && mkdir /data && chown bot /data
USER bot
ENV DB_PATH=/data/alifbo.db PORT=8080
VOLUME /data
EXPOSE 8080

CMD ["python", "bot.py"]
