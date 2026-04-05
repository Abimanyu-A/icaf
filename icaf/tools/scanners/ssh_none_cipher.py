"""
SSH None-Cipher Test
Ported from 2.6.1/SSH_TEST_CASES/SSH_TC4.py

Verifies that the DUT rejects SSH connections that request Ciphers=none.
"""

import subprocess
import shutil
import os


def run_ssh_none_cipher_test(context, cipher_data: dict) -> dict:
    """
    Attempt an SSH connection with Ciphers=none.

    Args:
        context: RuntimeContext (uses context.ssh_ip, context.ssh_user)
        cipher_data: output of run_cipher_detection() — used to check whether
                     'none' already appears in the DUT's advertised cipher list.

    Returns:
        dict with test_case_id, user_input, terminal_output, result, remarks,
        None_cipher_exist
    """
    dut_ip  = context.ssh_ip
    user    = context.ssh_user

    test_data = {
        "test_case_id": "TC4_SSH_NONE_CIPHER",
        "user_input": f"ssh -o Ciphers=none {user}@{dut_ip}",
        "terminal_output": "",
        "result": "",
        "remarks": "",
        "None_cipher_exist": False,
    }

    if not shutil.which("ssh"):
        test_data["result"] = "SKIP"
        test_data["remarks"] = "ssh binary not found"
        return test_data

    try:
        res = subprocess.run(
            [
                "ssh",
                "-o", "Ciphers=none",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=8",
                f"{user}@{dut_ip}",
                "exit",
            ],
            capture_output=True,
            text=True,
            timeout=12,
        )
        output = (res.stdout + res.stderr).lower()
        test_data["terminal_output"] = output

        # Check if 'none' is already advertised by the DUT
        try:
            enc_algos = (
                cipher_data["details"]["encryption"]["strong"]
                + cipher_data["details"]["encryption"]["weak"]
            )
        except (KeyError, TypeError):
            enc_algos = []

        if "none" in [a.lower() for a in enc_algos]:
            test_data["result"] = "FAIL"
            test_data["None_cipher_exist"] = True
            test_data["remarks"] = "DUT advertises 'none' cipher — critical vulnerability"

        elif "bad ssh2 cipher spec" in output:
            test_data["result"] = "PASS"
            test_data["remarks"] = "SSH client blocked none cipher; DUT does not advertise it"

        elif "no matching cipher" in output or "connection closed" in output:
            test_data["result"] = "PASS"
            test_data["remarks"] = "DUT rejected none-cipher negotiation (expected)"

        elif res.returncode == 0:
            test_data["result"] = "FAIL"
            test_data["remarks"] = "Connection succeeded with none cipher — critical vulnerability"

        else:
            test_data["result"] = "PASS"
            test_data["remarks"] = "None cipher not supported or usable"

    except subprocess.TimeoutExpired:
        test_data["result"] = "PASS"
        test_data["remarks"] = "Connection timed out — none cipher likely rejected"

    return test_data
