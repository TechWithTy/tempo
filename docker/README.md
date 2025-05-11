# Tempo Docker Setup

This directory contains all files needed to run Grafana Tempo with Docker Compose:

- `docker-compose.tempo.yml`: Compose file for running Tempo as a service.
- `tempo-config.example.yaml`: Example configuration for Tempo (local storage, metrics, etc).
- `.env.example`: Template for environment variables.
- `Dockerfile`: (Optional) Custom Dockerfile if you need to extend the base Tempo image.

## Usage

1. Copy `.env.example` to `.env` and fill in your secrets.
2. Adjust `tempo-config.example.yaml` as needed for your deployment.
3. Run Tempo via:
   ```sh
   docker-compose -f docker-compose.tempo.yml up -d
   ```
4. To build a custom image (if needed):
   ```sh
   docker build -t my-tempo-custom .
   ```

## Notes
- By default, this uses the official `grafana/tempo:latest` image. Use the Dockerfile if you need custom scripts/plugins.
- Mount your config file in Compose to `/etc/tempo/tempo.yaml`.
- Exposes Tempo UI on port 3200 and OTLP endpoints on 4317/4318.
