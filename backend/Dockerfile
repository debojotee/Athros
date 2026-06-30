FROM python:3.11-slim

# Install light system dependencies required by OpenCV (even headless)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code files into container
COPY . .

# Expose the API port
EXPOSE 8000

# Run FastAPI using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
