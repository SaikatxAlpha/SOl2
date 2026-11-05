FROM python:3.11-slim

WORKDIR /app

# CPU-only torch keeps the image a few GB smaller than the default CUDA build
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY app ./app
COPY saved_models ./saved_models
COPY seed_admin.py .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
