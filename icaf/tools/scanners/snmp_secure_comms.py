"""
SNMP Secure Communication Scanner
Ported from 2.6.1/SNMP_TEST_CASES/SNMP_TC2.py

Tests SNMPv3 in three security modes:
  authPriv    — should SUCCEED  (only accepted mode)
  authNoPriv  — should FAIL     (no privacy = weak)
  noAuthNoPriv — should FAIL    (unauthenticated)
"""

import subprocess
import os
from datetime import datetime

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _run_backend(cmd: str) -> str:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
    return result.stdout.strip()


def _run_snmp_phase(mode: str, dut_ip: str, snmp_user: str,
                    auth_pass: str, priv_pass: str) -> dict:
    data = {
        "command": "",
        "output": "",
        "success": False,
    }

    if mode == "authPriv":
        cmd = (
            f"snmpwalk -v3 -u {snmp_user} -l authPriv "
            f"-a SHA -A {auth_pass} -x AES -X {priv_pass} "
            f"{dut_ip} | head -n 3"
        )
    elif mode == "authNoPriv":
        cmd = (
            f"snmpwalk -v3 -u {snmp_user} -l authNoPriv "
            f"-a SHA -A {auth_pass} {dut_ip} | head -n 3"
        )
    else:  # noAuthNoPriv
        cmd = f"snmpwalk -v3 -u {snmp_user} -l noAuthNoPriv {dut_ip} | head -n 3"

    data["command"] = cmd
    output = _run_backend(cmd)
    data["output"] = output or "No response"
    data["success"] = bool(output.strip())

    return data


def run_snmp_secure_comms(context) -> dict:
    """
    Verify SNMPv3 security level enforcement.

    PASS conditions:
      - authPriv succeeds
      - authNoPriv and noAuthNoPriv both fail (no response)
    """
    dut_ip = context.ssh_ip
    snmp_user = getattr(context, "snmp_user", None) or "snmpuser"
    auth_pass = getattr(context, "snmp_auth_pass", None) or "AuthPass123"
    priv_pass = getattr(context, "snmp_priv_pass", None) or "PrivPass123"

    result = {
        "test_case_id": "TC2_SNMP_SECURE_COMMUNICATION",
        "authPriv": {},
        "authNoPriv": {},
        "noAuthNoPriv": {},
        "final_result": "",
    }

    result["authPriv"]     = _run_snmp_phase("authPriv",     dut_ip, snmp_user, auth_pass, priv_pass)
    result["authNoPriv"]   = _run_snmp_phase("authNoPriv",   dut_ip, snmp_user, auth_pass, priv_pass)
    result["noAuthNoPriv"] = _run_snmp_phase("noAuthNoPriv", dut_ip, snmp_user, auth_pass, priv_pass)

    auth_priv_ok  = result["authPriv"]["success"]
    auth_nopri_ok = result["authNoPriv"]["success"]
    noauth_ok     = result["noAuthNoPriv"]["success"]

    if not auth_priv_ok:
        result["final_result"] = "FAIL"
    elif auth_nopri_ok or noauth_ok:
        result["final_result"] = "FAIL"
    else:
        result["final_result"] = "PASS"

    return result
