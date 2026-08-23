FROM python:3.12-slim

WORKDIR /app

COPY mcp-server/requirements.txt mcp-server/
RUN pip install --no-cache-dir -r mcp-server/requirements.txt

COPY mcp-server/ mcp-server/
COPY src/ src/
COPY rules/ rules/
COPY pyproject.toml .

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["python", "mcp-server/server.py"]