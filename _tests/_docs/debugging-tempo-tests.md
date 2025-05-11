# Debugging Tempo Integration Tests

This document tracks the debugging steps, configuration changes, and outcomes during the process of getting Tempo integration tests running in this project.

---

## 1. **Container Fails to Start (Config Errors)**
- **Symptom:** Tempo container in restart loop, logs show YAML parse errors (e.g. `field index_downsample not found`, duplicate keys, etc.)
- **Actions:**
  - Cleaned up `tempo-config.example.yaml` to a minimal, valid config (removed unsupported/duplicate fields).
  - Ensured Docker Compose mounts the correct config file using an absolute Windows path and correct quoting.
- **Outcome:** Container now starts and loads the correct config.

---

## 2. **Docker Compose Volume Mount Issues on Windows**
- **Symptom:** `cat /etc/tempo/tempo.yaml` in the container fails (`No such file or directory`).
- **Actions:**
  - Switched to using absolute paths with forward slashes and quotes in `docker-compose.tempo.yml`.
  - Ran Docker Compose from PowerShell/CMD instead of Git Bash (to avoid path translation issues).
- **Outcome:** Config file now mounts correctly inside the container.

---

## 3. **Health Check/Fixture Issues in Tests**
- **Symptom:** Tests fail with `[pytest][warn] Docker Compose benign error: no service selected` or fail to detect healthy container in time.
- **Actions:**
  - Increased health check timeout in test fixture from 30s to 90s for slow container startup.
  - Improved fixture error messages for easier debugging.
  - Confirmed that the warning is benign if the container is already running and healthy.
- **Outcome:** Tests are less likely to fail due to slow startup. Benign warnings are now clearly logged.

---

## 4. **Security Warnings (Non-blocking)**
- **Symptom:** Warnings about default `SECRET_KEY` and `FIRST_SUPERUSER_PASSWORD` in logs.
- **Actions:**
  - Noted these are safe to ignore for local/dev, but must be changed for production.
- **Outcome:** Not a blocker for tests, but documented for future security hardening.

---

## 5. **Next Steps**
- If tests still fail, check:
  - Is the health endpoint (`http://localhost:3200/metrics`) available?
  - Are there actual test assertion errors? (Paste full output for targeted debugging.)
- Consider documenting any additional edge cases or troubleshooting steps as they arise.

---

_Last updated: 2025-05-11_
