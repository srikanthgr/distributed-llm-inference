FROM python:3.10-slim

# Install dependencies
RUN pip install --no-cache-dir \
    huggingface-hub==0.20.0 \
    openai==1.12.0 \
    requests==2.31.0

# Copy Python scripts
COPY model-acquisition.py /
COPY model-optimization.py /
COPY model-selection.py /
COPY test-service.py /
COPY inference-client.py /
COPY http-inference-request.py /

# Set working directory
WORKDIR /

# Default command (can be overridden)
CMD ["python", "--version"]

