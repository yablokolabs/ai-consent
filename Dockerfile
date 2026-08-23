FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN pip install --no-cache-dir --upgrade pip

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mcp-server/ mcp-server/

EXPOSE 8080

CMD ["python", "mcp-server/server.py"]