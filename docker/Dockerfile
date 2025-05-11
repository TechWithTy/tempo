# syntax=docker/dockerfile:1
FROM grafana/tempo:latest

# Optional: Add custom entrypoint scripts, healthchecks, or plugins here
# COPY ./your-custom-script.sh /docker-entrypoint-init.d/

# Example: Set a non-root user for security (uncomment if needed)
# USER 10001:10001

# Expose Tempo UI/API and OTLP ports
EXPOSE 3200 4317 4318

# Entrypoint and CMD are inherited from base image
