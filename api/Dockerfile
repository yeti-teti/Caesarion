# FROM python:3.11
FROM jupyter/base-notebook

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "index:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
