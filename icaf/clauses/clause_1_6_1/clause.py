from icaf.core.clause import BaseClause
from icaf.core.testcase import TestCase

from icaf.tools.scanners.nmap_scan import run_nmap_scan
from icaf.tools.scanners.cipher_support import run_cipher_detection
from icaf.tools.scanners.ssh_verify import run_ssh_verification
from icaf.tools.scanners.force_weak import run_ssh_weak_cipher_test
from icaf.tools.scanners.ssh_none_cipher import run_ssh_none_cipher_test
from icaf.tools.scanners.TLS_cipher_support import run_httpsCipher_detection
from icaf.tools.scanners.TLS_verify import run_tls_verification
from icaf.tools.scanners.https_weak_cipher import run_https_weak_cipher_test
from icaf.tools.scanners.https_null_cipher import run_https_null_test
from icaf.tools.scanners.snmp_version_check import run_snmp_version_check
from icaf.tools.scanners.snmp_secure_comms import run_snmp_secure_comms
from icaf.utils.dut_info import get_dut_info
from icaf.utils.oem_reader import run_oem_test


class Clause_1_6_1(BaseClause):

    name = "1.6.1 Cryptographic Based Secure Communication"

    def __init__(self, context):
        super().__init__(context)

    def run(self):

        results = []

        # ── Nmap Service Discovery ───────────────────────────────────────────
        nmap_result = run_nmap_scan(self.context)

        ssh_applicable   = bool(nmap_result.get("SSH"))
        https_applicable = bool(nmap_result.get("HTTPS"))
        snmp_applicable  = bool(nmap_result.get("SNMP"))

        # ── SSH Tests ────────────────────────────────────────────────────────
        cipher_result       = {}
        ssh_result          = {}
        weak_cipher_result  = {}
        none_cipher_result  = {}

        if ssh_applicable:
            cipher_result      = run_cipher_detection(self.context)
            ssh_result         = run_ssh_verification(self.context)
            weak_cipher_result = run_ssh_weak_cipher_test(self.context, cipher_result)
            none_cipher_result = run_ssh_none_cipher_test(self.context, cipher_result)

            results.append(TestCase(
                name="SSH Cipher Detection",
                description="Enumerate SSH encryption, MAC, KEX and host-key algorithms",
            ))
            results.append(TestCase(
                name="SSH Secure Communication Verification",
                description="Verify SSH session is encrypted using strong algorithms",
            ))
            results.append(TestCase(
                name="SSH Weak Cipher Negotiation",
                description="Ensure DUT rejects weak SSH cipher negotiation attempts",
            ))
            results.append(TestCase(
                name="SSH None-Cipher Rejection",
                description="Verify DUT rejects SSH connections using Ciphers=none",
            ))

        # ── HTTPS / TLS Tests ────────────────────────────────────────────────
        https_cipher_data      = {}
        https_data             = {}
        https_weak_result      = {}
        https_null_result      = {}

        if https_applicable:
            https_cipher_data = run_httpsCipher_detection(self.context)
            https_data        = run_tls_verification(self.context)
            https_weak_result = run_https_weak_cipher_test(self.context, https_cipher_data)
            https_null_result = run_https_null_test(self.context)

            results.append(TestCase(
                name="HTTPS TLS Cipher Detection",
                description="Enumerate TLS cipher suites supported by the DUT HTTPS service",
            ))
            results.append(TestCase(
                name="HTTPS TLS Secure Communication",
                description="Verify HTTPS session uses strong TLS configuration",
            ))
            results.append(TestCase(
                name="HTTPS Weak Cipher Negotiation",
                description="Ensure DUT rejects weak TLS cipher negotiation attempts",
            ))
            results.append(TestCase(
                name="HTTPS NULL Cipher Rejection",
                description="Verify DUT rejects TLS NULL (no-encryption) cipher suites",
            ))

        # ── SNMP Tests ───────────────────────────────────────────────────────
        snmp_v1v2_result  = {}
        snmp_v3_result    = {}

        if snmp_applicable:
            snmp_v1v2_result = run_snmp_version_check(self.context)
            snmp_v3_result   = run_snmp_secure_comms(self.context)

            results.append(TestCase(
                name="SNMP Version Check (v1/v2c disabled)",
                description="Verify SNMPv1 and SNMPv2c are disabled on the DUT",
            ))
            results.append(TestCase(
                name="SNMP Secure Communication (v3 authPriv only)",
                description="Verify only SNMPv3 authPriv is accepted; weaker modes rejected",
            ))

        # ── OEM Declaration ──────────────────────────────────────────────────
        oem_file = getattr(self.context, "oem_file", None)
        oem_data = {}
        if oem_file:
            oem_data = run_oem_test(oem_file)

        # ── DUT Info ─────────────────────────────────────────────────────────
        dut_info = get_dut_info(
            self.context.profile,
            self.context.ssh_user,
            self.context.ssh_ip,
            self.context.ssh_password,
        )

        # Store everything in context for the report generator
        self.context.scan_results = {
            "nmap":              nmap_result,
            "ssh_applicable":    ssh_applicable,
            "https_applicable":  https_applicable,
            "snmp_applicable":   snmp_applicable,
            "cipher":            cipher_result,
            "ssh":               ssh_result,
            "weak_cipher":       weak_cipher_result,
            "none_cipher":       none_cipher_result,
            "https_cipher":      https_cipher_data,
            "https":             https_data,
            "https_weak_cipher": https_weak_result,
            "https_null":        https_null_result,
            "snmp_v1v2":         snmp_v1v2_result,
            "snmp_v3":           snmp_v3_result,
            "oem":               oem_data,
            "dut_info":          dut_info,
        }

        return results
