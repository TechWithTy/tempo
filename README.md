# Tempo (Tracing Integration)

[![Tempo Tracing](https://img.shields.io/badge/Tempo-Tracing-blue)](https://www.cybershoptec.com)

A modular, production-ready tracing and observability integration for Python/FastAPI services, designed for seamless use with Grafana Tempo and OpenTelemetry. This submodule provides utilities, best practices, and test scaffolding to ensure robust distributed tracing in modern microservices and monoliths.

---

## 📁 Folder Structure & Conventions

```
tempo/
├── _docs/           # Markdown docs, best practices, diagrams, usage
├── _tests/          # Unit/integration tests for all core logic
├── config.py        # Singleton config (class-based, imports from global settings)
├── docker/          # Dockerfile, docker-compose, Tempo configs, .env.example
├── models/          # Pydantic models or trace schemas
├── exceptions/      # Custom exceptions for tracing
├── <core>.py        # Main implementation (trace logic, exporters, etc.)
├── README.md        # Main readme (this file)
```

- **_docs/**: All documentation, diagrams, and best practices for this module.
- **_tests/**: All tests for this module, including integration, async, and roundtrip tests.
- **config.py**: Singleton config pattern, imports from global settings, exposes all constants for this module.
- **docker/**: Containerization assets (Dockerfile, docker-compose, Tempo configs, .env.example, etc).
- **models/**: Pydantic models or schemas for trace payloads.
- **exceptions/**: Custom exception classes for robust error handling.
- **<core>.py**: Main implementation modules (e.g., trace logic, exporters, etc).

---

## 🏗️ Singleton & Config Pattern
- Use a single class (e.g., `TempoConfig`) in `config.py` to centralize all env, exporter, and integration settings.
- Import from global settings to avoid duplication and ensure DRY config.
- Document all config keys in `_docs/usage.md` and in this README.

---

## Features

- **Mockable and real trace roundtrip testing**
- **OpenTelemetry/Tempo compatibility**
- **Typed, documented test patterns**
- **Production best practices for trace ingestion and querying**
- **Easy integration with FastAPI and other Python frameworks**
- **CI/CD and DRY principles baked in**

## Usage

1. Add as a submodule:
   ```sh
   git submodule add <repo-url> backend/app/core/tempo
   ```
2. See [tests/_tests/](./_tests/) for integration examples.
3. Configure your tracing endpoints and environment variables as needed.

## Documentation
- [Project Website](https://www.cybershoptec.com)
- [Grafana Tempo](https://grafana.com/oss/tempo/)

## Tags
- tracing
- observability
- opentelemetry
- tempo
- fastapi
- python
- distributed-tracing
- monitoring
- ci-cd
- production-ready

## License
MIT License. See [LICENSE](./LICENSE).

---

> Maintained by [Cybershop Technologies](https://www.cybershoptec.com)
