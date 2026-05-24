"""Start the FastAPI backend and Next.js frontend together."""
import subprocess
import sys
import os
import time
import signal

ROOT = os.path.dirname(__file__)

procs = []

def shutdown(sig, frame):
    for p in procs:
        p.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

api_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api.main:app", "--reload", "--port", "8000"],
    cwd=ROOT,
)
procs.append(api_proc)

npm = "npm.cmd" if sys.platform == "win32" else "npm"
frontend_proc = subprocess.Popen(
    [npm, "run", "dev"],
    cwd=os.path.join(ROOT, "frontend"),
)
procs.append(frontend_proc)

print("\n  Backend:  http://localhost:8000")
print("  Frontend: http://localhost:3000\n")
print("  Press Ctrl+C to stop both servers.\n")

for p in procs:
    p.wait()
