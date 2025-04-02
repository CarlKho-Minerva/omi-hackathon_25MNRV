# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /omi-to-notion # Changed WORKDIR to match folder name, good practice

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port the application will run on
EXPOSE 8080

# Define the command to run the application
CMD ["uvicorn", "memory_dump_to_notion:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]