FROM jupyter/scipy-notebook:latest

USER root

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER jovyan

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app
WORKDIR /app

USER root
RUN chown -R jovyan:users /app
USER jovyan

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "index:app", "--host", "0.0.0.0", "--port", "8000"]
