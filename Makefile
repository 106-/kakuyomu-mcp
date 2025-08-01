.PHONY: help run run-shttp docker-build docker-run-stdio docker-run-http format check lint install clean

# Default target
help:
	@echo "Available commands:"
	@echo "  help        - Show this help message"
	@echo "  install     - Install dependencies with poetry"
	@echo "  run-stdio   - Run the MCP server directly (stdio mode)"
	@echo "  run-http   - Run the MCP server with streamable-http transport"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run  - Run the MCP server in Docker container"
	@echo "  format      - Format code with ruff"
	@echo "  check       - Check code with ruff (lint)"
	@echo "  lint        - Alias for check"
	@echo "  clean       - Clean up Docker images and containers"

# Install dependencies
install:
	poetry install

# Run the MCP server directly (stdio mode)
run-stdio:
	poetry run python kakuyomu_mcp/main.py --transport stdio

# Run the MCP server with streamable-http transport
run-http:
	poetry run python kakuyomu_mcp/main.py --transport streamable-http

# Build Docker image
docker-build:
	docker build -t kakuyomu-mcp .

# Run the MCP server in Docker container (stdio mode)
docker-run-stdio: docker-build
	docker run -i kakuyomu-mcp --transport stdio

# Run the MCP server in Docker container (streamable-http mode)
docker-run-http: docker-build
	docker run -p 9468:9468 kakuyomu-mcp --transport streamable-http

# Format code with ruff
format:
	poetry run ruff format .

# Check code with ruff (lint)
check:
	poetry run ruff check .

# Alias for check
lint: check

# Clean up Docker images and containers
clean:
	docker rmi kakuyomu-mcp kakuyomu-mcp-test 2>/dev/null || true
	docker container prune -f