"""Start both real servers, verify frontend/proxy and run HTTP rehearsal; then stop."""

from pathlib import Path
import subprocess, sys, os, time, urllib.request, json, tempfile, secrets

root = Path(__file__).resolve().parent
npm = "npm.cmd" if os.name == "nt" else "npm"
processes = []
# Run entirely against an isolated temporary database. Credentials are ephemeral.
smoke_dir = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(smoke_dir.name) / "smoke.db")
os.environ["UPLOAD_DIR"] = str(Path(smoke_dir.name) / "uploads")
os.environ["APP_ENV"] = "development"
os.environ["CHAKRA_DEMO_PASSWORD"] = secrets.token_urlsafe(32)
subprocess.run(
    [sys.executable, "-m", "app.auth_bootstrap", "--demo"],
    cwd=root / "backend",
    check=True,
)
with tempfile.TemporaryDirectory() as log_dir:
    logs = []
    try:
        for name, command, cwd in [
            (
                "backend",
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                root / "backend",
            ),
            ("frontend", [npm, "run", "dev"], root / "frontend"),
        ]:
            log = open(Path(log_dir) / (name + ".log"), "w+")
            logs.append(log)
            processes.append(
                subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
            )
        for url in ["http://127.0.0.1:8000/health", "http://127.0.0.1:5173/"]:
            deadline = time.monotonic() + 20
            while True:
                try:
                    with urllib.request.urlopen(url, timeout=2) as response:
                        assert response.status == 200
                        content = response.read()
                    break
                except (OSError, AssertionError):
                    if time.monotonic() > deadline:
                        raise RuntimeError("Server did not become ready: " + url)
                    time.sleep(0.1)
        with urllib.request.urlopen("http://127.0.0.1:5173/api/health") as response:
            assert json.load(response)["status"] == "ok"
        with urllib.request.urlopen("http://127.0.0.1:5173/src/main.tsx") as response:
            assert response.status == 200
        print(
            "PASS real FastAPI health, Vite HTML/module serving and Vite → FastAPI proxy",
            flush=True,
        )
        for module in ["HomePage", "WorkflowDiagram", "DecisionPanel"]:
            with urllib.request.urlopen(
                "http://127.0.0.1:5173/src/" + module + ".tsx"
            ) as response:
                assert response.status == 200
        with urllib.request.urlopen(
            "http://127.0.0.1:5173/api/public/pathway-policy"
        ) as response:
            assert len(json.load(response)["pbs_levels"]) == 5
        request = urllib.request.Request(
            "http://127.0.0.1:5173/api/public/pathway-explorer",
            data=json.dumps(
                {"pbs": "L5", "soh_percent": 100, "quotes_available": True}
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            result = json.load(response)
            assert (
                result["safety_state"] == "CRITICAL_HOLD"
                and result["recommended_pathway"] is None
                and result["persistent"] is False
            )
        print(
            "PASS public homepage modules, policy and non-persistent explorer through the real proxy",
            flush=True,
        )
        subprocess.run(
            [sys.executable, "circular_demo.py"], cwd=root / "backend", check=True
        )
        subprocess.run(
            [sys.executable, "organisation_demo.py"], cwd=root / "backend", check=True
        )
    except Exception:
        for log in logs:
            log.flush()
            log.seek(0)
            print(log.read())
        raise
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        for log in logs:
            log.close()

smoke_dir.cleanup()
