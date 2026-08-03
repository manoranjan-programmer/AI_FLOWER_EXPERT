# Flower AI Expert – Chatbot & Knowledge Microservice

FastAPI microservice handling AI botanical chatbot generation, FAISS semantic vector retrieval, Helsinki-NLP offline translation, MongoDB search history, Google OAuth 2.0, and analytics.

## Responsibilities
- Vector search & RAG over flower knowledge base (`knowledge.py`).
- LLM response generation and streaming (`chatbot.py`).
- Offline language translation (`translation.py`).
- User authentication & search history storage in MongoDB Atlas (`auth.py`).
- Active flower context selection (`POST /flower/select`).

## Running Locally

1. Create a virtual environment and install requirements:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Start the service (runs on port **8000** by default):
   ```bash
   python app.py
   # or
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

## Deployment

Deploy independently to Render, Railway, Docker, or your cloud provider.

**Runtime:** `python-3.11.11`  
**Environment Variables:**
- `PORT`: 8000
- `MONGO_URI`: MongoDB Atlas Connection String
- `JWT_SECRET`: Secure JWT Secret Key
- `GOOGLE_CLIENT_ID`: Google OAuth 2.0 Client ID
