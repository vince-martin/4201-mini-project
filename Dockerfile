FROM python:3.12-slim

WORKDIR /app

RUN pip install flask

RUN pip install redis

COPY main.py .

EXPOSE 8080

CMD [ "python", "main.py" ]