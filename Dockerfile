# Use official Python lightweight image
FROM python:3.12-slim

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (ffmpeg is required for Whisper audio processing)
# We update apt-get and clean up in the same layer to reduce image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy dependency file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies and pre-download the SpaCy model and Whisper model
# This ensures the 12MB NLP model and 460MB Voice model are baked into the image, avoiding runtime downloads
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm && \
    python -c 'from faster_whisper import WhisperModel; WhisperModel("small", device="cpu", compute_type="int8")'

# Copy the rest of the application code
COPY . .

# Create the data directory explicitly to be used as a mount point for SQLite WAL logs
RUN mkdir -p /app/data
# Point SQLite database location to the persistent data volume via Environmental Variable or directly in code
# (Assuming codebase defaults to ptclinvoice_sre.db in CWD, we'll run uvicorn from /app)
ENV DB_PATH=/app/data/ptclinvoice_sre.db

# Expose port for FastAPI
EXPOSE 8000

# Start the uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
