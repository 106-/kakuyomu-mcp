FROM python:3.10-slim

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy poetry configuration files
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Copy source code
COPY kakuyomu_mcp/ ./kakuyomu_mcp/

# Install dependencies
RUN poetry install --only=main

# Expose port for StreamableHTTP MCP server
EXPOSE 9468

# Set environment variables for HTTP server
ENV PORT=9468
ENV HOST=0.0.0.0

# Run the MCP server with StreamableHTTP
CMD ["python", "-m", "kakuyomu_mcp.main", "--transport", "streamable-http"]