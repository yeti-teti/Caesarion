# FROM python:3.11
FROM jupyter/base-notebook

USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/data
RUN chown -R jovyan:users /app/data

RUN pip install --upgrade pip setuptools wheel

USER jovyan

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "index:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
