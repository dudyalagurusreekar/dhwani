"""
Phase 3.5 Live End-to-End Trust-Boundary & Authentication Verification Script
Spawns live FastAPI backend on port 8001 and Next.js BFF on port 3001,
verifies trust boundaries, confused deputy remediation, negative security tests, and health probes.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

BACKEND_PORT = 8001
FRONTEND_PORT = 3001
TEST_SECRET_KEY = "dhwani_live_trust_boundary_secret_789"
WRONG_SECRET_KEY = "attacker_invalid_forged_key_000"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")


def find_npm():
    npm_path = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm_path:
        npm_path = r"C:\Program Files\nodejs\npm.cmd"
    return npm_path


def wait_for_http(url, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "E2E-Verifier"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status in (200, 401, 404):
                    return True
        except urllib.error.HTTPError as e:
            if e.code in (200, 401, 404):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8"), dict(e.headers)


def http_post(url, json_data=None, headers=None):
    headers = headers or {}
    data = None
    if json_data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_data).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8"), dict(e.headers)


def http_delete(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {}, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8"), dict(e.headers)


def main():
    print("=" * 75)
    print("Phase 3.5 Live Trust-Boundary & Authentication Verification")
    print("=" * 75)

    backend_env = os.environ.copy()
    backend_env["DHWANI_AUTH_REQUIRED"] = "true"
    backend_env["DHWANI_API_KEY"] = TEST_SECRET_KEY
    backend_env["PYTHONPATH"] = PROJECT_ROOT

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(BACKEND_PORT),
    ]

    npm_bin = find_npm()
    frontend_env = os.environ.copy()
    frontend_env["DHWANI_BACKEND_URL"] = f"http://127.0.0.1:{BACKEND_PORT}"
    frontend_env["DHWANI_API_KEY"] = TEST_SECRET_KEY
    frontend_env["DHWANI_DEMO_MODE"] = "true"

    frontend_cmd = [npm_bin, "run", "start", "--", "-p", str(FRONTEND_PORT)]

    print(f"[*] Starting FastAPI backend on port {BACKEND_PORT}...")
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=PROJECT_ROOT,
        env=backend_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print(f"[*] Starting Next.js BFF on port {FRONTEND_PORT}...")
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=FRONTEND_DIR,
        env=frontend_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    results = []

    try:
        # Wait for backend
        backend_ready = wait_for_http(f"http://127.0.0.1:{BACKEND_PORT}/health", timeout=15)
        assert backend_ready, "FastAPI backend failed to start within 15 seconds."
        print("[+] FastAPI backend is live.")

        # Wait for frontend
        frontend_ready = wait_for_http(f"http://127.0.0.1:{FRONTEND_PORT}/health", timeout=20)
        assert frontend_ready, "Next.js frontend failed to start within 20 seconds."
        print("[+] Next.js BFF is live.")

        # -------------------------------------------------------------
        # Test 1: Direct backend protected endpoint WITHOUT credentials -> 401
        # -------------------------------------------------------------
        status, body, _ = http_get(f"http://127.0.0.1:{BACKEND_PORT}/api/system/status")
        passed = (status == 401)
        results.append(("Direct backend without auth rejected (401)", passed, f"Status: {status}"))
        print(f"  [1] Direct backend without auth: HTTP {status} (Expected 401) -> {'PASS' if passed else 'FAIL'}")

        # -------------------------------------------------------------
        # Test 2: Direct backend protected endpoint WITH valid X-API-Key -> 200
        # -------------------------------------------------------------
        status, body, _ = http_get(
            f"http://127.0.0.1:{BACKEND_PORT}/api/system/status",
            headers={"X-API-Key": TEST_SECRET_KEY},
        )
        passed = (status == 200 and "OPERATIONAL" in body)
        results.append(("Direct backend with valid key succeeds (200)", passed, f"Status: {status}"))
        print(f"  [2] Direct backend with valid key: HTTP {status} (Expected 200) -> {'PASS' if passed else 'FAIL'}")

        # -------------------------------------------------------------
        # Test 3: Public Demo Route on BFF (/api/system/status) succeeds in demo mode
        # -------------------------------------------------------------
        status, body, _ = http_get(f"http://127.0.0.1:{FRONTEND_PORT}/api/system/status")
        passed = (status == 200 and "OPERATIONAL" in body)
        results.append(("Public demo route /api/system/status accessible in demo mode (200)", passed, f"Status: {status}"))
        print(f"  [3] Public demo route /api/system/status: HTTP {status} (Expected 200) -> {'PASS' if passed else 'FAIL'}")

        # -------------------------------------------------------------
        # Test 4: Protected Operational Endpoint (/api/incidents) WITHOUT client key MUST BE REJECTED -> 401
        # (Fix for Confused Deputy Vulnerability)
        # -------------------------------------------------------------
        status, body, _ = http_get(f"http://127.0.0.1:{FRONTEND_PORT}/api/incidents")
        passed = (status == 401 and "requires client authentication" in body)
        results.append(("Anonymous request to protected /api/incidents rejected (401)", passed, f"Status: {status}"))
        print(f"  [4] Anonymous /api/incidents rejected: HTTP {status} (Expected 401) -> {'PASS' if passed else 'FAIL'}")

        # -------------------------------------------------------------
        # Test 5: Protected Operational Endpoint (/api/incidents) WITH valid client key -> 200
        # -------------------------------------------------------------
        status, body, _ = http_get(
            f"http://127.0.0.1:{FRONTEND_PORT}/api/incidents",
            headers={"X-API-Key": TEST_SECRET_KEY},
        )
        passed = (status == 200 and "incidents" in body)
        results.append(("Authorized client request to /api/incidents succeeds (200)", passed, f"Status: {status}"))
        print(f"  [5] Authorized client /api/incidents: HTTP {status} (Expected 200) -> {'PASS' if passed else 'FAIL'}")

        # -------------------------------------------------------------
        # Test 6: Protected Operational Endpoint (/api/incidents) WITH invalid client key -> 401
        # -------------------------------------------------------------
        status, body, _ = http_get(
            f"http://127.0.0.1:{FRONTEND_PORT}/api/incidents",
            headers={"X-API-Key": WRONG_SECRET_KEY},
        )
        passed = (status == 401)
        results.append(("Forged client key to /api/incidents rejected by backend (401)", passed, f"Status: {status}"))
        print(f"  [6] Forged client key /api/incidents rejected: HTTP {status} (Expected 401) -> {'PASS' if passed else 'FAIL'}")

        # -------------------------------------------------------------
        # Test 7: BFF rejects unallowed route -> 404
        # -------------------------------------------------------------
        status, body, _ = http_get(f"http://127.0.0.1:{FRONTEND_PORT}/api/unallowed/admin/panel")
        passed = (status == 404 and "not accessible via the BFF proxy" in body)
        results.append(("BFF rejects unallowed route (404)", passed, f"Status: {status}"))
        print(f"  [7] BFF unallowed route rejection: HTTP {status} (Expected 404) -> {'PASS' if passed else 'FAIL'}")

        # -------------------------------------------------------------
        # Test 8: BFF rejects forbidden HTTP method -> 405
        # -------------------------------------------------------------
        status, body, _ = http_delete(f"http://127.0.0.1:{FRONTEND_PORT}/api/incidents")
        passed = (status == 405 and "Method DELETE is not allowed" in body)
        results.append(("BFF rejects forbidden method (405)", passed, f"Status: {status}"))
        print(f"  [8] BFF forbidden method rejection: HTTP {status} (Expected 405) -> {'PASS' if passed else 'FAIL'}")

        # -------------------------------------------------------------
        # Test 9: Public health probe exposes zero secrets -> 200
        # -------------------------------------------------------------
        status, body, _ = http_get(f"http://127.0.0.1:{FRONTEND_PORT}/health")
        passed = (status == 200 and TEST_SECRET_KEY not in body and "api_key" not in body.lower())
        results.append(("Frontend /health reveals zero secrets (200)", passed, f"Status: {status}"))
        print(f"  [9] Frontend /health leak check: HTTP {status} -> {'PASS' if passed else 'FAIL'}")

    finally:
        print("[*] Cleaning up live server processes...")
        try:
            backend_proc.terminate()
            backend_proc.wait(timeout=3)
        except Exception:
            backend_proc.kill()

        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend_proc.pid)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            try:
                frontend_proc.kill()
            except Exception:
                pass

    print("\n" + "=" * 75)
    print("PHASE 3.5 LIVE TRUST-BOUNDARY VERIFICATION RESULTS:")
    all_passed = all(r[1] for r in results)
    for name, passed, detail in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name} ({detail})")
    print(f"\nFinal Result: {'ALL 9 TESTS PASSED' if all_passed else 'FAILURES DETECTED'}")
    print("=" * 75)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
