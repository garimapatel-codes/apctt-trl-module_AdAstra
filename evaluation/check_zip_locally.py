"""check_zip_locally.py - run the PACKED zip through the kit's own server, like the organizer's
Submission 1 diagnostic run (the same 3 public sample cases: USGS-SDG-012, 040, 061).

What it does, step by step:
  1. unpacks Ad_Astra_submission.zip into a fresh folder (so it tests exactly what you upload)
  2. writes a server configuration for it, with the package hash from the zip's submission.json
     (the server refuses to start if the code in the zip does not match that hash)
  3. starts the kit server, checks GET /v1/package says "verified"
  4. builds the 3 request files with the kit's tools/get_public_cases.py
  5. sends each case, waits, and prints status, TRL, timings and any output issue
  6. stops the server and prints PASS or FAIL like the organizer's feedback

Run it with the KIT's server Python (the .venv of the kit, not the base environment):
    ~/work/apctt-participant-kit-0.5.0-cpu/.venv/bin/python check_zip_locally.py

Defaults can be changed with environment variables: KIT, ZIP, PDFS, WORK, PORT, BASE_PY, MODELS.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

HOME = Path.home()
KIT = Path(os.environ.get("KIT", HOME / "work/apctt-participant-kit-0.5.0-cpu")).resolve()
ZIP = Path(os.environ.get("ZIP", HOME / "work/Ad_Astra_submission.zip")).resolve()
PDFS = Path(os.environ.get("PDFS", "/mnt/c/Users/aeror/Documents/projects/apctt_iitb/cases_pdf"))
WORK = Path(os.environ.get("WORK", HOME / "work/zip_check")).resolve()
PORT = int(os.environ.get("PORT", "8011"))
BASE = f"http://127.0.0.1:{PORT}"
CASES = ["USGS-SDG-012", "USGS-SDG-040", "USGS-SDG-061"]


def stop(message: str) -> None:
    print(f"\nSTOPPED: {message}")
    sys.exit(1)


def call(method: str, path: str, body: dict | None = None, timeout: float = 120):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.headers, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, error.headers, json.loads(error.read() or b"{}")


def find_base_python_and_models() -> tuple[Path, Path]:
    """Take them from your existing config/my.local.json (step 6 of the kit README) if it exists."""
    base_py = os.environ.get("BASE_PY")
    models = os.environ.get("MODELS") or os.environ.get("APCTT_MODEL_STORE")
    mine = KIT / "config/my.local.json"
    if mine.is_file():
        config = json.loads(mine.read_text(encoding="utf-8"))
        if not base_py and config.get("worker", {}).get("python"):
            # abspath, NOT resolve(): bin/python of a virtual environment is a link, and following
            # it lands on the bare interpreter without the environment's packages
            base_py = os.path.abspath(mine.parent / config["worker"]["python"])
        if not models:
            models = config.get("worker", {}).get("extra_env", {}).get("APCTT_MODEL_STORE")
    base_py = Path(os.path.abspath(base_py or HOME / "work/apctt-env/base/bin/python"))
    models = Path(models or HOME / "work/models")
    return base_py, models


def main() -> None:
    print("=" * 72)
    print("Local copy of the organizer's Submission 1 check")
    print("=" * 72)
    for what, path in (("kit", KIT), ("zip", ZIP), ("PDF folder", PDFS)):
        if not path.exists():
            stop(f"{what} not found: {path}")
    base_py, models = find_base_python_and_models()
    if not base_py.is_file():
        stop(f"base environment Python not found: {base_py} (set BASE_PY=...)")
    if not models.is_dir():
        stop(f"model store not found: {models} (set MODELS=...)")
    probe = subprocess.run(
        [str(base_py), "-c", "import sys, torch, transformers, sentence_transformers, pypdfium2; "
         "print(sys.prefix, torch.__version__, transformers.__version__)"],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        print(probe.stderr[-1500:])
        stop(f"{base_py} is not the base environment (torch/transformers/pypdfium2 missing). "
             "Set BASE_PY to the base environment's bin/python")
    print(f"base env     {probe.stdout.strip()}")
    print(f"zip          {ZIP}")
    print(f"base Python  {base_py}")
    print(f"model store  {models}")

    # 1. a fresh copy of exactly what is in the zip
    if WORK.exists():
        shutil.rmtree(WORK)
    package = WORK / "package"
    with zipfile.ZipFile(ZIP) as archive:
        archive.extractall(package)
    (package / "assets").mkdir(exist_ok=True)
    submission = json.loads((package / "submission.json").read_text(encoding="utf-8"))
    declared = submission.get("declared_package_sha256")
    print(f"package hash {declared}")

    # 2. server configuration (the kit's dev.json with our module, our hash, our base and models)
    config = json.loads((KIT / "config/dev.json").read_text(encoding="utf-8"))
    config["bind_port"] = PORT
    config["data_dir"] = str(WORK / "server_data")
    config["worker_tmp_dir"] = str(WORK / "worker_tmp")
    config["checklist_path"] = str(KIT / "contracts/checklist.official.json")
    config["compute"]["device"] = submission.get("compute", {}).get("device", "cpu")
    config["module"].update(
        package_id=submission["package_id"],
        entrypoint="participant_module.adapter:AssessmentModule",
        module_root=str(package),
        package_root=str(package / "participant_module"),
        asset_root=str(package / "assets"),
        declared_package_sha256=declared,
        example_only=False,
        settings=submission.get("settings", {}),
    )
    config["worker"]["python"] = str(base_py)
    config["worker"]["extra_env"] = {"APCTT_MODEL_STORE": str(models)}
    config_path = WORK / "config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    # 3. request files for the 3 diagnostic cases (the kit's own tool; it also checks the PDFs)
    requests = WORK / "requests"
    made = subprocess.run(
        [sys.executable, str(KIT / "tools/get_public_cases.py"), "--make-requests", *CASES,
         "--dir", str(PDFS), "--out", str(requests)],
        cwd=KIT, capture_output=True, text=True,
    )
    if made.returncode != 0:
        print(made.stdout[-2000:], made.stderr[-2000:])
        stop("could not build the request files (see above)")

    # 4. start the server
    env = dict(os.environ)
    env["PYTHONPATH"] = str(KIT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    log = open(WORK / "server.log", "w", encoding="utf-8")
    server = subprocess.Popen(
        [sys.executable, "-m", "apctt_server", "--profile", "dev", "--config", str(config_path)],
        cwd=KIT, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(120):
            if server.poll() is not None:
                log.flush()
                print((WORK / "server.log").read_text(encoding="utf-8")[-3000:])
                stop("the server refused to start (its message is above)")
            try:
                status, _, _ = call("GET", "/health/ready", timeout=2)
                if status == 200:
                    break
            except OSError:
                pass
            time.sleep(0.5)
        else:
            stop("the server did not become ready within 60 s")

        _, _, pkg = call("GET", "/v1/package")
        verified = pkg.get("verification_status")
        print(f"\nserver package: {pkg.get('package_id')} | verification_status {verified} | "
              f"hash matches zip: {pkg.get('verified_package_sha256') == declared}")
        if verified != "verified":
            print(json.dumps(pkg, indent=2)[:2000])

        # 5. the 3 cases
        print(f"\n{'case':14s} {'status':10s} {'TRL':>3s}  {'met':>3s}  {'load s':>6s} {'total s':>7s}  problems")
        all_ok = verified == "verified"
        for case_id in CASES:
            body = json.loads((requests / f"{case_id}.json").read_text(encoding="utf-8"))
            body["request_id"] = f"zipcheck-{case_id}-{time.time_ns() % 10**9}"
            status, headers, job = call("POST", "/v1/assessments", body)
            if status != 202:
                all_ok = False
                print(f"{case_id:14s} REJECTED {status} {json.dumps(job.get('error', {}))[:300]}")
                continue
            while job["job_status"] != "finished":
                time.sleep(1)
                _, _, job = call("GET", headers["Location"])
            result, diag = job["result"], job.get("diagnostics", {})
            timings = diag.get("timings_ms", {}) or {}
            load_s = (timings.get("load") or 0) / 1000
            total_s = (timings.get("total") or 0) / 1000
            met = sum(1 for v in result.get("criterion_status", {}).values() if v == "met")
            problems = []
            if job.get("result_origin") != "module":
                problems.append(f"result made by the {job.get('result_origin')}")
            if result.get("error_code"):
                problems.append(f"error {result['error_code']}")
            if "failure" in diag:
                problems.append(diag["failure"].get("message", ""))
            problems += [f"{i['path']} {i['rule']}" for i in diag.get("output_issues", [])]
            problems += [f"warning {w}" for w in diag.get("warning_codes", [])]
            logs = sorted((WORK / "server_data/jobs").glob("*/stderr.log"),
                          key=lambda f: f.stat().st_mtime)
            log_text = logs[-1].read_text(encoding="utf-8", errors="replace") if logs else ""
            warn = [line.strip() for line in log_text.splitlines()
                    if line.startswith(("pipeline failed", "reader not loaded", "judge not loaded",
                                        "model store "))]
            if met == 0 or warn:
                problems.append("NOT WORKING PROPERLY: " + (" | ".join(warn)[:600] if warn else
                                "no criterion met - the module used its emergency fallback"))
            ok = result.get("assessment_status") in ("completed", "abstained") and not [
                p for p in problems if not p.startswith("warning")]
            all_ok &= ok
            print(f"{case_id:14s} {result.get('assessment_status', '?'):10s} "
                  f"{str(result.get('predicted_trl')):>3s}  {met:>3d}  {load_s:6.1f} {total_s:7.1f}  "
                  f"{'; '.join(problems) or '-'}")
            print(f"{'':14s} timings_ms {timings}")
            (WORK / f"{case_id}.result.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()

    print("\n" + "=" * 72)
    print("RESULT: PASS - the zip runs on the kit server and every case gives a valid result"
          if all_ok else "RESULT: FAIL - see the problems above")
    print(f"Full results: {WORK}/<case>.result.json   Server log: {WORK}/server.log")
    print(f"Module logs:  {WORK}/server_data/jobs/<id>/stderr.log")
    print("=" * 72)


if __name__ == "__main__":
    main()
