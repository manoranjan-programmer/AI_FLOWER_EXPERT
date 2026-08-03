# Flower AI Expert – Classifier Microservice

Dedicated lightweight FastAPI microservice for flower image classification powered by ONNX Runtime.

## Responsibilities
- Accepts image uploads via `POST /predict`.
- Runs fast, low-memory ONNX Runtime CPU inference (`flower_classifier.onnx`).
- Returns predicted `{ flower_name, confidence, class_id }`.

## Running Locally

1. Create a virtual environment and install requirements:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Start the service (runs on port **8001** by default):
   ```bash
   python app.py
   # or
   uvicorn app:app --host 0.0.0.0 --port 8001
   ```

## Deployment

Deploy independently to Render, Railway, Hugging Face Spaces, or Docker.

**Runtime:** `python-3.11.11`  
**Environment Variables:**
- `PORT`: 8001
- `HF_REPO_ID`: `manoranjan-programmer/flower-ai-model`
- `CLASSIFIER_MODEL_NAME`: `flower_classifier.onnx`
