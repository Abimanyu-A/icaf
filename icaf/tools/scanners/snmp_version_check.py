"""
SNMP Version Check Scanner
Ported from 2.6.1/SNMP_TEST_CASES/SNMP_TC1.py

Tests whether SNMPv1 and SNMPv2c are disabled on the DUT (they should be).
"""

import subprocess
import os
from datetime import datetime

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _run_snmp_backend(command: str) -> str:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=20
        )
        return result.stdout.strip()
    except Exception as e:
        return str(e)


def run_snmp_version_check(context) -> dict:
    """
    Check whether SNMPv1 and SNMPv2c respond (they should NOT on a hardened DUT).

    Returns:
        dict with keys: test_case_id, user_input_v1, terminal_output_v1,
        user_input_v2c, terminal_output_v2c, validation_details, final_result
    """
    dut_ip = context.ssh_ip

    result = {
        "test_case_id": "TC1_SNMP_VERSION_CHECK",
        "user_input_v1": "",
        "terminal_output_v1": "",
        "v1_screenshot": "",
        "user_input_v2c": "",
        "terminal_output_v2c": "",
        "v2c_screenshot": "",
        "validation_details": {"v1_success": False, "v2c_success": False},
        "final_result": "",
    }

    # SNMPv1
    cmd_v1 = (
        f"snmpwalk -v1 -c public {dut_ip} "
        "| grep -E 'STRING|INTEGER|OID|iso' | head -n 3"
    )
    result["user_input_v1"] = cmd_v1
    v1_output = _run_snmp_backend(cmd_v1)
    result["terminal_output_v1"] = v1_output or "No response (secure)"
    result["validation_details"]["v1_success"] = bool(v1_output.strip())

    # SNMPv2c
    cmd_v2 = (
        f"snmpwalk -v2c -c public {dut_ip} "
        "| grep -E 'STRING|INTEGER|OID|iso' | head -n 3"
    )
    result["user_input_v2c"] = cmd_v2
    v2_output = _run_snmp_backend(cmd_v2)
    result["terminal_output_v2c"] = v2_output or "No response (secure)"
    result["validation_details"]["v2c_success"] = bool(v2_output.strip())

    # PASS = both v1 and v2c are disabled (no response)
    if result["validation_details"]["v1_success"] or result["validation_details"]["v2c_success"]:
        result["final_result"] = "FAIL"
    else:
        result["final_result"] = "PASS"

    return result
