"""
icaf/cli/preflight.py
─────────────────────────────────────────────────────────────────────────────
Pre-flight checker and auto-installer for all ICAF system dependencies.

Run via:
    icaf doctor                  (integrated CLI command)
    python setup_check.py        (standalone — same logic)

What it checks
──────────────
  System binaries   : tcpdump, tshark, wireshark, nmap, ssh, openssl,
                      snmpwalk, xdotool, scrot, wmctrl, gnome-terminal,
                      firefox, geckodriver
  Permissions       : tcpdump cap_net_raw capability
  Display           : DISPLAY / WAYLAND_DISPLAY for GUI tools
  Python packages   : all packages from requirements.txt / pyproject.toml
  Firefox + Gecko   : version match and PATH availability

For every missing binary it attempts to install via apt-get (Debian/Ubuntu).
For geckodriver it downloads the correct release from GitHub automatically.
For tcpdump it grants cap_net_raw+eip with setcap (requires sudo once).
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    _RICH = True
except ImportError:
    _RICH = False


# ── Constants ────────────────────────────────────────────────────────────────

GECKODRIVER_API = (
    "https://api.github.com/repos/mozilla/geckodriver/releases/latest"
)

APT_PACKAGES: dict[str, str] = {
    "tcpdump":        "tcpdump",
    "tshark":         "tshark",
    "wireshark":      "wireshark",
    "nmap":           "nmap",
    "ssh":            "openssh-client",
    "openssl":        "openssl",
    "snmpwalk":       "snmp",
    "xdotool":        "xdotool",
    "scrot":          "scrot",
    "wmctrl":         "wmctrl",
    "gnome-terminal": "gnome-terminal",
    "firefox":        "firefox",
    "geckodriver":    None,   # handled separately
    "pkill":          "procps",
}

# Python packages that must be importable
PYTHON_PACKAGES: list[tuple[str, str]] = [
    ("typer",         "typer"),
    ("rich",          "rich"),
    ("selenium",      "selenium"),
    ("yaml",          "pyyaml"),
    ("docx",          "python-docx"),
    ("pyautogui",     "pyautogui"),
    ("openpyxl",      "openpyxl"),
    ("dotenv",        "python-dotenv"),
    ("pandas",        "pandas"),
]

# GUI tools that need a display
GUI_TOOLS = {"xdotool", "scrot", "wmctrl", "gnome-terminal", "wireshark", "firefox"}


# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str
    fixed: bool = False
    warning: bool = False


@dataclass
class PreflightReport:
    results: List[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)

    @property
    def failures(self) -> List[CheckResult]:
        return [r for r in self.results if not r.ok and not r.warning]

    @property
    def warnings(self) -> List[CheckResult]:
        return [r for r in self.results if r.warning]

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def _apt_install(pkg: str) -> bool:
    """Try to install a package via apt-get. Returns True on success."""
    try:
        result = subprocess.run(
            ["sudo", "apt-get", "install", "-y", pkg],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _pip_install(pkg: str) -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def _has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _tcpdump_has_cap() -> bool:
    """Return True if tcpdump has cap_net_raw capability set."""
    tcpdump_path = shutil.which("tcpdump")
    if not tcpdump_path:
        return False
    result = _run(["getcap", tcpdump_path])
    return "cap_net_raw" in result.stdout


def _grant_tcpdump_cap() -> bool:
    """Grant cap_net_raw+eip to tcpdump binary. Requires sudo."""
    tcpdump_path = shutil.which("tcpdump")
    if not tcpdump_path:
        return False
    result = subprocess.run(
        ["sudo", "setcap", "cap_net_raw+eip", tcpdump_path],
        capture_output=True, text=True
    )
    return result.returncode == 0


def _get_firefox_version() -> Optional[str]:
    result = _run(["firefox", "--version"])
    if result.returncode != 0:
        return None
    match = re.search(r"(\d+\.\d+)", result.stdout)
    return match.group(1) if match else None


def _get_geckodriver_version() -> Optional[str]:
    gd = shutil.which("geckodriver")
    if not gd:
        return None
    result = _run(["geckodriver", "--version"])
    match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
    return match.group(1) if match else None


def _download_geckodriver() -> bool:
    """Download the latest geckodriver from GitHub and install to /usr/local/bin."""
    try:
        with urllib.request.urlopen(GECKODRIVER_API, timeout=10) as resp:
            data = json.loads(resp.read())

        tag = data["tag_name"]
        machine = platform.machine().lower()

        # Map arch
        if machine in ("x86_64", "amd64"):
            arch = "linux64"
        elif machine in ("aarch64", "arm64"):
            arch = "linux-aarch64"
        else:
            arch = "linux64"  # fallback

        asset_name = f"geckodriver-{tag}-{arch}.tar.gz"
        download_url = next(
            (a["browser_download_url"] for a in data["assets"]
             if a["name"] == asset_name),
            None
        )

        if not download_url:
            return False

        with tempfile.TemporaryDirectory() as tmp:
            archive = os.path.join(tmp, asset_name)
            urllib.request.urlretrieve(download_url, archive)

            subprocess.run(
                ["tar", "-xzf", archive, "-C", tmp],
                check=True, capture_output=True
            )

            gd_tmp = os.path.join(tmp, "geckodriver")
            if not os.path.exists(gd_tmp):
                return False

            # Install to /usr/local/bin (may need sudo)
            dest = "/usr/local/bin/geckodriver"
            result = subprocess.run(
                ["sudo", "cp", gd_tmp, dest],
                capture_output=True
            )
            if result.returncode != 0:
                # Try without sudo (user has write access)
                shutil.copy2(gd_tmp, dest)

            os.chmod(dest, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                     stat.S_IROTH | stat.S_IXOTH)

        return shutil.which("geckodriver") is not None

    except Exception:
        return False


# ── Individual checks ─────────────────────────────────────────────────────────

def check_os() -> CheckResult:
    system = platform.system()
    release = platform.release()
    if system != "Linux":
        return CheckResult(
            "Operating System",
            ok=False,
            message=f"ICAF requires Linux. Detected: {system} {release}",
        )
    return CheckResult(
        "Operating System",
        ok=True,
        message=f"Linux {release}"
    )


def check_python() -> CheckResult:
    v = sys.version_info
    ok = v >= (3, 9)
    return CheckResult(
        "Python version",
        ok=ok,
        message=f"Python {v.major}.{v.minor}.{v.micro}"
                + ("" if ok else " — Python 3.9+ required")
    )


def check_display() -> CheckResult:
    has = _has_display()
    return CheckResult(
        "Display (DISPLAY / WAYLAND_DISPLAY)",
        ok=True,
        warning=not has,
        message=(
            os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
            if has
            else "No display detected — GUI tools (wireshark, firefox, scrot, "
                 "xdotool, gnome-terminal) will not work. Set DISPLAY=:0 or "
                 "run inside an X session."
        )
    )


def check_binary(name: str, auto_fix: bool) -> CheckResult:
    path = shutil.which(name)
    if path:
        return CheckResult(name, ok=True, message=path)

    apt_pkg = APT_PACKAGES.get(name)

    if name == "geckodriver":
        # Special handler
        if not auto_fix:
            return CheckResult(
                name, ok=False,
                message="Not found. Run with --fix to download automatically."
            )
        ok = _download_geckodriver()
        if ok:
            return CheckResult(
                name, ok=True, fixed=True,
                message=f"Downloaded and installed to /usr/local/bin/geckodriver"
            )
        return CheckResult(
            name, ok=False,
            message="Auto-download failed. Install manually from "
                    "https://github.com/mozilla/geckodriver/releases"
        )

    if not apt_pkg:
        return CheckResult(name, ok=False, message="Not found. No known apt package.")

    if not auto_fix:
        return CheckResult(
            name, ok=False,
            message=f"Not found. Run with --fix to install via: "
                    f"sudo apt-get install {apt_pkg}"
        )

    installed = _apt_install(apt_pkg)
    if installed and shutil.which(name):
        return CheckResult(
            name, ok=True, fixed=True,
            message=f"Installed via apt ({apt_pkg}) → {shutil.which(name)}"
        )
    return CheckResult(
        name, ok=False,
        message=f"apt install {apt_pkg} failed or binary still not on PATH. "
                f"Try manually: sudo apt-get install {apt_pkg}"
    )


def check_tcpdump_capability(auto_fix: bool) -> CheckResult:
    if not shutil.which("tcpdump"):
        return CheckResult(
            "tcpdump capability (cap_net_raw)",
            ok=False,
            message="tcpdump binary not found — install first."
        )

    if _tcpdump_has_cap():
        return CheckResult(
            "tcpdump capability (cap_net_raw)",
            ok=True,
            message="cap_net_raw+eip is set — can capture without root."
        )

    # Check if running as root (alternative)
    if os.geteuid() == 0:
        return CheckResult(
            "tcpdump capability (cap_net_raw)",
            ok=True,
            message="Running as root — tcpdump can capture without setcap."
        )

    if not auto_fix:
        return CheckResult(
            "tcpdump capability (cap_net_raw)",
            ok=False,
            message="cap_net_raw not set. Run with --fix, or manually: "
                    f"sudo setcap cap_net_raw+eip {shutil.which('tcpdump')}"
        )

    granted = _grant_tcpdump_cap()
    if granted:
        return CheckResult(
            "tcpdump capability (cap_net_raw)",
            ok=True, fixed=True,
            message=f"Granted cap_net_raw+eip on {shutil.which('tcpdump')}"
        )
    return CheckResult(
        "tcpdump capability (cap_net_raw)",
        ok=False,
        message=f"setcap failed. Run manually: "
                f"sudo setcap cap_net_raw+eip {shutil.which('tcpdump')}"
    )


def check_tshark_group() -> CheckResult:
    """
    tshark requires the user to be in the 'wireshark' group for live capture.
    (For PCAP file reading this isn't needed, but warn anyway.)
    """
    if not shutil.which("tshark"):
        return CheckResult(
            "tshark group (wireshark)",
            ok=True,
            warning=True,
            message="tshark not installed — skipping group check."
        )
    result = _run(["groups"])
    in_group = "wireshark" in result.stdout.split()
    if in_group:
        return CheckResult(
            "tshark group (wireshark)",
            ok=True,
            message=f"User is in the 'wireshark' group."
        )
    return CheckResult(
        "tshark group (wireshark)",
        ok=True,
        warning=True,
        message="User is not in the 'wireshark' group. Live capture may fail. "
                "Fix: sudo usermod -aG wireshark $USER  (then re-login)"
    )


def check_python_package(import_name: str, pip_name: str, auto_fix: bool) -> CheckResult:
    try:
        __import__(import_name)
        return CheckResult(f"Python: {pip_name}", ok=True, message="Installed")
    except ImportError:
        pass

    if not auto_fix:
        return CheckResult(
            f"Python: {pip_name}", ok=False,
            message=f"Not installed. Run with --fix or: pip install {pip_name}"
        )

    ok = _pip_install(pip_name)
    try:
        __import__(import_name)
        return CheckResult(
            f"Python: {pip_name}", ok=True, fixed=True,
            message=f"Installed via pip"
        )
    except ImportError:
        return CheckResult(
            f"Python: {pip_name}", ok=False,
            message=f"pip install {pip_name} ran but import still fails."
        )


def check_geckodriver_firefox_match() -> CheckResult:
    """Warn if geckodriver and Firefox are both present but versions may diverge."""
    gd = shutil.which("geckodriver")
    ff = shutil.which("firefox")
    if not gd or not ff:
        return CheckResult(
            "Firefox / geckodriver compatibility",
            ok=True,
            warning=True,
            message="Cannot check — one or both binaries missing."
        )
    ff_ver = _get_firefox_version() or "unknown"
    gd_ver = _get_geckodriver_version() or "unknown"
    return CheckResult(
        "Firefox / geckodriver compatibility",
        ok=True,
        message=f"Firefox {ff_ver}  |  geckodriver {gd_ver}"
    )


def check_nmap_scripts() -> CheckResult:
    """Verify nmap has the ssl-enum-ciphers script (needed for cipher scans)."""
    if not shutil.which("nmap"):
        return CheckResult(
            "nmap ssl-enum-ciphers script",
            ok=True,
            warning=True,
            message="nmap not installed — skipping script check."
        )
    result = _run(["nmap", "--script-help", "ssl-enum-ciphers"])
    if result.returncode == 0:
        return CheckResult(
            "nmap ssl-enum-ciphers script",
            ok=True,
            message="ssl-enum-ciphers script available."
        )
    return CheckResult(
        "nmap ssl-enum-ciphers script",
        ok=False,
        message="ssl-enum-ciphers script not found. "
                "Install nmap-scripts: sudo apt-get install nmap"
    )


# ── Main runner ───────────────────────────────────────────────────────────────

def run_preflight(auto_fix: bool = False) -> PreflightReport:
    report = PreflightReport()

    # --- Environment ---
    report.add(check_os())
    report.add(check_python())
    report.add(check_display())

    # --- System binaries ---
    for binary in APT_PACKAGES:
        result = check_binary(binary, auto_fix)

        # Downgrade GUI-tool failures to warnings when there's no display
        if not result.ok and binary in GUI_TOOLS and not _has_display():
            result.warning = True
            result.ok = True
            result.message += "  [no display — GUI tool will be skipped at runtime]"

        report.add(result)

    # --- Special permissions ---
    report.add(check_tcpdump_capability(auto_fix))
    report.add(check_tshark_group())

    # --- Compatibility checks ---
    report.add(check_geckodriver_firefox_match())
    report.add(check_nmap_scripts())

    # --- Python packages ---
    for import_name, pip_name in PYTHON_PACKAGES:
        report.add(check_python_package(import_name, pip_name, auto_fix))

    return report


# ── Output ────────────────────────────────────────────────────────────────────

def _status_icon(result: CheckResult) -> str:
    if result.fixed:
        return "[bold green]  FIXED [/bold green]"
    if result.warning:
        return "[bold yellow]  WARN  [/bold yellow]"
    if result.ok:
        return "[bold green]  OK    [/bold green]"
    return "[bold red]  FAIL  [/bold red]"


def print_report(report: PreflightReport) -> None:
    if not _RICH:
        # Plain fallback
        for r in report.results:
            icon = "OK" if r.ok else ("WARN" if r.warning else "FAIL")
            if r.fixed:
                icon = "FIXED"
            print(f"[{icon}]  {r.name}: {r.message}")
        if report.passed:
            print("\nAll checks passed.")
        else:
            print(f"\n{len(report.failures)} check(s) failed.")
        return

    console = Console()

    console.print(
        Panel("[bold cyan]ICAF Pre-flight Check[/bold cyan]",
              border_style="bright_magenta", padding=(0, 2))
    )

    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold white")
    table.add_column("Status", width=9, justify="center")
    table.add_column("Check", style="white", min_width=36)
    table.add_column("Detail", style="dim white")

    for r in report.results:
        table.add_row(_status_icon(r), r.name, r.message)

    console.print(table)

    total   = len(report.results)
    ok      = sum(1 for r in report.results if r.ok and not r.warning)
    fixed   = sum(1 for r in report.results if r.fixed)
    warns   = len(report.warnings)
    fails   = len(report.failures)

    summary_parts = [
        f"[green]{ok} passed[/green]",
        f"[yellow]{warns} warnings[/yellow]",
        f"[red]{fails} failed[/red]",
    ]
    if fixed:
        summary_parts.append(f"[cyan]{fixed} auto-fixed[/cyan]")

    console.print("  " + "   ".join(summary_parts))
    console.print()

    if report.passed:
        console.print(
            "[bold green]  ICAF is ready to run.[/bold green]\n"
        )
    else:
        console.print(
            "[bold red]  Some checks failed. Re-run with --fix to attempt "
            "auto-installation, or resolve them manually.[/bold red]\n"
        )


# ── Typer command (used when imported into icaf CLI) ──────────────────────────

def register_doctor_command(app) -> None:
    """
    Call this from icaf/cli/main.py to add `icaf doctor` to the CLI.

    Usage in main.py:
        from icaf.cli.preflight import register_doctor_command
        register_doctor_command(app)
    """
    import typer

    @app.command(name="doctor")
    def doctor(
        fix: bool = typer.Option(
            False, "--fix",
            help="Attempt to auto-install missing dependencies."
        )
    ):
        """Check and optionally install all ICAF system dependencies."""
        report = run_preflight(auto_fix=fix)
        print_report(report)
        if not report.passed:
            raise typer.Exit(code=1)


# ── Standalone entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="ICAF pre-flight dependency checker"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to auto-install missing system and Python dependencies."
    )
    args = parser.parse_args()

    report = run_preflight(auto_fix=args.fix)
    print_report(report)
    sys.exit(0 if report.passed else 1)