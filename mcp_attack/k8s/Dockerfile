FROM python:3.12-slim AS builder

WORKDIR /build
COPY mcp_attack/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

LABEL org.opencontainers.image.title="mcp-audit" \
      org.opencontainers.image.description="MCP Red Teaming / Security Scanner for Kubernetes" \
      org.opencontainers.image.source="https://github.com/tms/agentsmith"

RUN groupadd -r scanner && useradd -r -g scanner -s /sbin/nologin scanner

COPY --from=builder /install /usr/local
COPY mcp_attack/ /app/mcp_attack/

WORKDIR /app
USER scanner

ENTRYPOINT ["python", "-m", "mcp_attack"]
CMD ["--k8s-discover", "--verbose"]
