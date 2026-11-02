"""The Help screenshot tour (S103): one command, tooling/help-shots.bat.

In one try/finally it takes the machine's e2e lock, makes the lane 9 database and the sample files,
starts the e2e backend (5019) and Vite (5189) on lane 9, loads the e2e seed and the tour's standard data
(setup_tour.py), runs Playwright with frontend/help-tour/tour.config.js, converts the shots to lossless
WebP, then stops both servers and releases the lock, also after a failure.

Everything it writes is under scratch/help-shots/: shots/*.png, webp/*.webp, data.json, files/, the logs,
results/ (Playwright's outputDir); the lane's files folder scratch/e2e-data/lane9/ (e2e_backend.py); and
Vite's cache scratch/e2e-vite-lane9/.
Lane 9 and its ports (5019, 5189) are written in tooling/help/tour.py, tooling/help/setup_tour.py,
frontend/help-tour/tour.config.js and frontend/help-tour/documents.tour.js: change all four together.
Run it with the backend's environment (Pillow): uv run --project backend python tooling/help/tour.py
"""
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tooling" / "e2e"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
LANE = 9
os.environ["E2E_LANE"] = str(LANE)
import run_lanes  # noqa: E402
import make_photo  # noqa: E402
import setup_tour  # noqa: E402

FRONTEND = ROOT / "frontend"
OUT = ROOT / "scratch" / "help-shots"
BACKEND_URL = f"http://127.0.0.1:{5010 + LANE}"
FRONTEND_URL = f"http://127.0.0.1:{5180 + LANE}"
START_SECONDS = 180


def wait_for(url, seconds=START_SECONDS):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=3)
            return
        except OSError:
            time.sleep(1)
    raise SystemExit(f"{url} did not come up")


def stop(process):
    """The process and its children (shell=True starts uv or npx, which start the server)."""
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)


def to_webp():
    """Lossless WebP copies of the shots, for help/*/shots/ (D5)."""
    from PIL import Image
    target = OUT / "webp"
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    for png in sorted((OUT / "shots").glob("*.png")):
        with Image.open(png) as image:
            image.save(target / f"{png.stem}.webp", "WEBP", lossless=True, quality=100, method=4)


def run():
    shutil.rmtree(OUT / "shots", ignore_errors=True)
    shutil.rmtree(OUT / "results", ignore_errors=True)
    (OUT / "shots").mkdir(parents=True)
    make_photo.make_files(OUT / "files")
    run_lanes.create_databases(LANE)
    env = {**os.environ, "E2E_LANE": str(LANE)}
    backend = vite = None
    with open(OUT / "backend.log", "w") as backend_log, open(OUT / "vite.log", "w") as vite_log:
        try:
            backend = subprocess.Popen("uv run --project ../backend python ../tooling/e2e/e2e_backend.py",
                                       cwd=FRONTEND, shell=True, env=env, stdout=backend_log,
                                       stderr=subprocess.STDOUT)
            vite = subprocess.Popen(f"npx vite --host 127.0.0.1 --port {5180 + LANE} --strictPort", cwd=FRONTEND,
                                    shell=True, stdout=vite_log, stderr=subprocess.STDOUT,
                                    env={**env, "YANTRA_API_URL": BACKEND_URL,
                                         "E2E_VITE_CACHE_DIR": f"../scratch/e2e-vite-lane{LANE}"})
            wait_for(BACKEND_URL + "/api/health")
            wait_for(FRONTEND_URL)
            print("servers up", flush=True)
            seed = subprocess.run(f"uv run --project ../backend python ../tooling/e2e/seed_e2e.py {BACKEND_URL}",
                                  cwd=FRONTEND, shell=True, env=env)
            if seed.returncode:
                return seed.returncode
            setup_tour.main()
            tour = subprocess.run("npx playwright test -c help-tour/tour.config.js", cwd=FRONTEND, shell=True,
                                  env=env)
            to_webp()
            return tour.returncode
        finally:
            for process in (vite, backend):
                if process is not None:
                    stop(process)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lock_file = run_lanes.main_scratch() / run_lanes.LOCK_NAME
    with run_lanes.one_run_at_a_time(lock_file):
        code = run()
    print(f"The tour {'passed' if code == 0 else 'failed'}; shots in {OUT / 'shots'}, WebP in {OUT / 'webp'}.")
    return code


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.exit(main())
