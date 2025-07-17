FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (optional: for better reload performance)
RUN apt-get update && apt-get install -y build-essential

# Install app dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your source code
COPY . .

# Expose default FastAPI port
EXPOSE 8000

# Use reload mode like fastapi dev
CMD ["fastapi", "dev", "main.py", "--host", "0.0.0.0", "--port", "15434"]
