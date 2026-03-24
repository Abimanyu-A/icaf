"""
steps/analyze_pcap_step.py
──────────────────────────────────────────────────────────────────────────────
Runs tshark against the captured PCAP file with a display filter and extracts
rich per-packet detail (not just frame numbers).

Improvements over original
───────────────────────────
• Extracts multiple fields per packet: frame number, timestamp, source/dest
  IP, protocol, info summary, TLS version, cipher suite, SSH fields,
  SNMP version/community, encrypted-PDU flag.
• Stores a structured list of packet dicts on context.pcap_packets so other
  steps (WiresharkPacketScreenshotStep, report generator) can use them.
• Still sets context.matched_frame to the first matching frame for Wireshark.
• Raises a clear exception if tshark is not installed.
• Logs a human-readable one-liner per matched packet.
• Accepts an optional max_packets limit (default 50) to avoid flooding logs.
"""

import subprocess
import shutil
from icaf.core.step import Step
from icaf.utils.logger import logger


# Fields extracted from every matched packet
_TSHARK_FIELDS = [
    "frame.number",
    "frame.time_relative",
    "ip.src",
    "ip.dst",
    "frame.protocols",
    "_ws.col.Info",
    # TLS
    "tls.handshake.version",
    "tls.handshake.ciphersuite",
    "tls.record.content_type",
    # SSH
    "ssh.protocol",
    "ssh.encryption_algorithms_client_to_server",
    # SNMP
    "snmp.version",
    "snmp.community",
    "snmp.msgAuthoritativeEngineID",
    # HTTP/HTTPS
    "http.response.code",
    "http.request.method",
]


def _build_tshark_cmd(pcap: str, display_filter: str, max_packets: int) -> list:
    cmd = [
        "tshark",
        "-r", pcap,
        "-Y", display_filter,
        "-T", "fields",
        "-E", "separator=|",
        "-E", "header=y",
        "-c", str(max_packets),
    ]
    for field in _TSHARK_FIELDS:
        cmd += ["-e", field]
    return cmd


def _parse_tshark_output(stdout: str) -> list[dict]:
    """
    Parse pipe-delimited tshark output (with header row) into a list of dicts.
    Empty fields become empty strings.
    """
    lines = stdout.strip().splitlines()
    if len(lines) < 2:          # header + at least one data row
        return []

    headers = lines[0].split("|")
    packets = []
    for line in lines[1:]:
        values = line.split("|")
        # Pad to header length in case trailing fields are empty
        while len(values) < len(headers):
            values.append("")
        packets.append(dict(zip(headers, values)))
    return packets


class AnalyzePcapStep(Step):
    """
    Analyse a PCAP file with tshark using a display filter.

    Parameters
    ----------
    filter_expr : str
        Any valid Wireshark/tshark display filter, e.g.
        ``"ssh"``, ``"tls"``, ``"snmp"``, ``"tcp.port == 50051"``
    max_packets : int
        Maximum number of matching packets to extract (default 50).
    """

    def __init__(self, filter_expr: str, max_packets: int = 50):
        super().__init__("Analyze PCAP")
        self.filter_expr = filter_expr
        self.max_packets = max_packets

    def execute(self, context):
        if not shutil.which("tshark"):
            raise EnvironmentError(
                "tshark is not installed or not on PATH. "
                "Install with: sudo apt-get install tshark"
            )

        pcap = context.pcap_file
        if not pcap:
            raise ValueError("context.pcap_file is not set — run PcapStartStep first")

        cmd = _build_tshark_cmd(pcap, self.filter_expr, self.max_packets)

        logger.info(
            "Analysing PCAP: filter='%s'  file=%s",
            self.filter_expr, pcap,
        )

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode not in (0, 1):   # 1 = no packets (not an error)
            logger.warning("tshark stderr: %s", result.stderr.strip())

        packets = _parse_tshark_output(result.stdout)

        if not packets:
            # Non-fatal — log a warning and continue; the TC can decide
            logger.warning(
                "No packets matched filter '%s' in %s",
                self.filter_expr, pcap,
            )
            context.matched_frame  = None
            context.pcap_packets   = []
            context.pcap_summary   = f"No packets matched filter: {self.filter_expr}"
            return

        # Set matched_frame to first hit (used by WiresharkPacketScreenshotStep)
        context.matched_frame = packets[0].get("frame.number", "1")

        # Store full structured list for report / screenshot step
        context.pcap_packets = packets

        # Build a human-readable one-line summary per packet for the log
        summary_lines = []
        for pkt in packets:
            fn   = pkt.get("frame.number", "?")
            src  = pkt.get("ip.src",  "?")
            dst  = pkt.get("ip.dst",  "?")
            info = pkt.get("_ws.col.Info", "")
            proto_stack = pkt.get("frame.protocols", "")
            line = f"  frame={fn}  {src} → {dst}  [{proto_stack}]  {info}"
            summary_lines.append(line)
            logger.info(line)

        context.pcap_summary = "\n".join(summary_lines)

        logger.info(
            "PCAP analysis complete: %d packet(s) matched filter '%s'",
            len(packets), self.filter_expr,
        )

        # Store key protocol fields as top-level context attrs for easy access
        first = packets[0]
        context.pcap_tls_version     = first.get("tls.handshake.version", "")
        context.pcap_tls_cipher      = first.get("tls.handshake.ciphersuite", "")
        context.pcap_ssh_protocol    = first.get("ssh.protocol", "")
        context.pcap_ssh_kex         = first.get("ssh.kex.algorithms", "")
        context.pcap_snmp_version    = first.get("snmp.version", "")