FROM astral/uv:python3.13-bookworm-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync
COPY . .
CMD ["uv", "run", "main.py"]
