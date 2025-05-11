import os
import subprocess
import time
import pytest
import requests

TEMPO_HOST = os.getenv("TEMPO_HOST", "127.0.0.1")
TEMPO_PORT = int(os.getenv("TEMPO_PORT", 3200))
TEMPO_HEALTH_URL = f"http://{TEMPO_HOST}:{TEMPO_PORT}/metrics"
DOCKER_COMPOSE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "docker", "docker-compose.tempo.yml"
)

@pytest.fixture(scope="session", autouse=True)
def ensure_tempo_running():
    """
    Ensure that the Tempo container is running and healthy before tests.
    If not running, start it using Docker Compose.
    """
    def is_tempo_healthy():
        hosts = ["127.0.0.1", "localhost"]
        for host in hosts:
            try:
                url = f"http://{host}:{TEMPO_PORT}/metrics"
                resp = requests.get(url, timeout=2)
                if resp.status_code == 200:
                    return True
            except Exception:
                continue
        return False

    if not is_tempo_healthy():
        print("[pytest] Tempo not running, starting container...")
        try:
            result = subprocess.run([
                "docker-compose",
                "-f",
                DOCKER_COMPOSE_PATH,
                "up",
                "-d",
                "tempo"
            ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            stdout = e.stdout or ""
            # Allow benign errors (e.g. 'no service selected', already running)
            if ("no service selected" in stderr.lower() or "no service selected" in stdout.lower()):
                print(f"[pytest][warn] Docker Compose benign error: {stderr or stdout}")
            else:
                print(f"[pytest][error] Docker Compose failed:\nSTDOUT: {stdout}\nSTDERR: {stderr}")
                raise
        # * Increased timeout to 90s for slow container startups or slow Windows Docker
        timeout = 90
        for _ in range(timeout):
            if is_tempo_healthy():
                break
            time.sleep(1)
        else:
            print("[pytest][error] Tempo health endpoint did not become available after 90 seconds.")
            raise RuntimeError("Tempo did not become healthy in time!")
    else:
        print("[pytest] Tempo is already running.")
    yield
    # Optionally tear down container after tests; not always desired in CI
    # Example: Uncomment the following to stop container after session:
    # subprocess.run([
    #     "docker-compose",
    #     "-f",
    #     DOCKER_COMPOSE_PATH,
    #     "down"
    # ], check=True)

def clear_tempo_data():
    """
    Cleanup routine for test traces in Tempo.
    Implement if your test setup writes traces.
    """
    # Implement cleanup logic if needed (e.g., delete test traces via API or restart container)
    pass

@pytest.fixture(autouse=False)
def tempo_test_context():
    """
    Fixture for isolating Tempo test data.
    Yields a context for writing/reading traces, and can clean up after.
    """
    clear_tempo_data()
    yield
    clear_tempo_data()
