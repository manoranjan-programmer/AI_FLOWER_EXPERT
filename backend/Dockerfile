FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV PORT=8000

EXPOSE 8000

CMD ["python","-m","uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000","--reload"]