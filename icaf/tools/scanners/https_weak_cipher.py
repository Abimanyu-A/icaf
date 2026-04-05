"""
HTTPS Weak Cipher Negotiation Test
Ported from 2.6.1/HTTPS_TEST_CASES/HTTPS_TC3.py

Attempts to negotiate each detected weak TLS cipher against the DUT.
The DUT should REJECT all of them (PASS = none negotiated).
"""

import subprocess
import os
from datetime import datetime

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def run_https_weak_cipher_test(context, cipher_test_data: dict) -> dict:
    """
    Try to connect using each weak TLS cipher found by the cipher scanner.

    Args:
        context: RuntimeContext (uses context.ssh_ip)
        cipher_test_data: output of run_httpsCipher_detection()

    Returns:
        dict with test_case_id, results list, final_result
    """
    dut_ip = context.ssh_ip

    test_data = {
        "test_case_id": "TC7_HTTPS_WEAK_CIPHER_NEGOTIATION",
        "results": [],
        "final_result": "PASS",
    }

    try:
        weak_tls12 = cipher_test_data["details"]["TLSv1.2"]["ciphers"].get("weak", [])
        weak_tls13 = cipher_test_data["details"]["TLSv1.3"]["ciphers"].get("weak", [])
    except (KeyError, TypeError):
        test_data["final_result"] = "SKIP"
        return test_data

    all_weak = [(v, c) for v in ("TLSv1.2",) for c in weak_tls12] + \
               [(v, c) for v in ("TLSv1.3",) for c in weak_tls13]

    for tls_version, cipher in all_weak:
        if tls_version == "TLSv1.2":
            cmd = (
                f"echo | openssl s_client -connect {dut_ip}:443 "
                f"-tls1_2 -cipher {cipher} 2>&1 "
                "| grep -Ei 'Cipher is|handshake failure|no shared cipher|no cipher match'"
            )
        else:
            cmd = (
                f"echo | openssl s_client -connect {dut_ip}:443 "
                f"-tls1_3 -ciphersuites {cipher} 2>&1 "
                "| grep -Ei 'Cipher is|handshake failure|no shared cipher|no cipher match'"
            )

        try:
            res = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=5
            )
            output = (res.stdout + res.stderr).strip().lower()
        except subprocess.TimeoutExpired as e:
            output = ((e.stdout or "") + (e.stderr or "")).strip().lower()

        # Determine if the weak cipher was negotiated
        if "cipher is (none)" in output or "handshake failure" in output \
                or "no shared cipher" in output or not output:
            negotiated = False
        elif "cipher is" in output:
            negotiated = True
        else:
            negotiated = False

        test_data["results"].append({
            "tls_version": tls_version,
            "cipher": cipher,
            "command": cmd,
            "negotiated": negotiated,
            "terminal_output": output,
        })

        if negotiated:
            test_data["final_result"] = "FAIL"
            return test_data  # fail-fast

    return test_data
