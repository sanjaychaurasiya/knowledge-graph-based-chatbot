FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY .env .env

COPY main.py ./

EXPOSE 7860
EXPOSE 7687

CMD ["gradio", "main.py"]