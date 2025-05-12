FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .

COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8080"]
