# Use an official Python runtime as a parent image
# PyTorch Geometric can be heavy, so we use a standard slim image.
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for some Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Dependencies for this vector. Listed inline rather than copied from a
# requirements.txt: the repo keeps a single unified requirements.txt at the
# root, which is outside this image's build context.
RUN pip install --no-cache-dir \
    torch torch-geometric pandas numpy networkx \
    scikit-learn faker google-generativeai

# Copy the rest of the application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the adversarial loop when the container starts
CMD ["python", "main.py"]
