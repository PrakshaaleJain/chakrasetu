"""Launch local backend and frontend. Install dependencies and seed first."""

from pathlib import Path
import subprocess, sys, os, time

root = Path(__file__).resolve().parent
npm = "npm.cmd" if os.name == "nt" else "npm"
processes = []
try:
    processes.append(
        subprocess.Popen(
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
            cwd=root / "backend",
        )
    )
    processes.append(subprocess.Popen([npm, "run", "dev"], cwd=root / "frontend"))
    print(
        "ChakraSetu frontend: http://127.0.0.1:5173 | API: http://127.0.0.1:8000/docs",
        flush=True,
    )
    while all(p.poll() is None for p in processes):
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
