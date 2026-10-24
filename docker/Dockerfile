FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MODEL_PATH=/model/model.pkl

WORKDIR /app

COPY app/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/app.py /app/app.py
COPY model/model.pkl /model/model.pkl

EXPOSE 5000

CMD ["python", "app.py"]
