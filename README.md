# ICAF - ITSAR Compliance Automation Framework

ICAF is a Python-based automation framework for evaluating device compliance against ITSAR (IT Security Assurance Requirements) clauses. It automates the execution of structured test cases across multiple network protocols and management interfaces, collects evidence, and produces formal compliance reports.

---

## Features

- Automated execution of ITSAR clause test cases
- Support for SSH, SNMPv3, HTTPS, gRPC/gNMI, and TLS protocol testing
- Device-type-aware execution via a profile system (Linux, Cisco, OpenWrt, Alpine)
- OAM (Operations, Administration and Management) protocol parsing from Excel input
- Integrated network scanning using Nmap, cipher analysis, and TLS verification
- PCAP capture and Wireshark packet screenshot capture for evidence collection
- Automated browser interaction via Selenium for web-based management interfaces
- Structured Word document report generation per clause
- Rich terminal UI with live progress feedback

---

## Project Structure

```
icaf/
├── cli/            # Typer-based command-line interface
├── clauses/        # Clause implementations and test cases
│   ├── clause_1_1_1/   # Management Plane Access Control (SNMPv3, SSH, HTTPS, gRPC/gNMI)
│   └── clause_1_6_1/   # Cryptographic-Based Secure Communication
├── core/           # Engine, clause runner, step runner, base classes
├── config/         # Directory setup and profile loading
├── device/         # Device type detection
├── evidence/       # Evidence file management
├── oam/            # OAM Excel parsing and protocol verification
├── profile/        # YAML and XLSX device profiles
├── reporting/      # Report generation (per-clause Word documents, front page)
├── runtime/        # Execution context
├── steps/          # Reusable test step implementations
├── terminal/       # Terminal session management
├── tools/
│   ├── report_helpers/ # Formatting, headings, tables, screenshots for reports
│   └── scanners/       # Nmap, TLS, SSH, SNMP, cipher scanning tools
└── utils/          # Logging, DUT info, login detection, OEM reader
```

---

## Requirements

- Python 3.9 or higher
- Google Chrome and ChromeDriver (for Selenium-based browser steps)
- Nmap (for network scanning steps)
- Wireshark/TShark (for PCAP analysis steps)

Python dependencies are listed in `requirements.txt`:

```
typer
rich
selenium
pyyaml
python-docx
pyautogui
openpyxl
python-dotenv
pandas
```

---

## Installation

```bash
git clone <repository-url>
cd icaf
pip install -e .
```

Or install dependencies directly:

```bash
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` to `.env` and populate with the target device credentials:

```bash
cp .env.example .env
```

**.env fields:**

| Variable          | Description                              |
|-------------------|------------------------------------------|
| `SSH_USER`        | SSH username for the device under test   |
| `SSH_IP`          | IP address of the device under test      |
| `SSH_PASSWORD`    | SSH password                             |
| `SNMP_USER`       | SNMPv3 username                          |
| `SNMP_AUTH_PASS`  | SNMPv3 authentication password           |
| `SNMP_PRIV_PASS`  | SNMPv3 privacy password                  |
| `SNMP_COMMUNITY`  | SNMP community string                    |
| `WEB_LOGIN_URL`   | URL of the device web management portal  |
| `WEB_USERNAME`    | Web interface username                   |
| `WEB_PASSWORD`    | Web interface password                   |
| `TESTBED_DIAGRAM` | Path to testbed diagram image            |

SSH credentials (`SSH_USER`, `SSH_IP`, `SSH_PASSWORD`) are required for all execution modes.

---

## Usage

### Run a specific clause

```bash
icaf run --clause 1.1.1
icaf run --clause 1.6.1
```

### Run a specific section

```bash
icaf run --section 1.1
```

### Run with a device profile

```bash
icaf run --clause 1.6.1 --profile alpine
```

Available profiles: `default`, `alpine`, `metasploitable`

### Run with OAM input

```bash
icaf run --clause 1.6.1 --oam path/to/oam.xlsx
```

OAM mode parses an Excel file to detect and verify the management protocols in use on the device before executing the clause.

### Run via Python directly

```bash
python run.py run --clause 1.1.1 --profile default
```

---

## Supported Clauses

### Clause 1.1.1 - Management Plane Access Control

Tests authentication and access control across management protocols:

| Test Case | Description                        |
|-----------|------------------------------------|
| TC1       | SNMPv3 positive authentication     |
| TC2       | SNMPv3 invalid credentials         |
| TC3       | SSH mutual authentication          |
| TC4       | SSH correct public key              |
| TC5       | SSH incorrect public key            |
| TC6       | HTTPS valid login                   |
| TC7       | HTTPS invalid login                 |
| TC8       | gRPC/gNMI mutual authentication    |

### Clause 1.6.1 - Cryptographic-Based Secure Communication

Scans and verifies the cryptographic posture of the device across protocols:

- Nmap service discovery
- SSH cipher support and verification
- SSH weak and null cipher enforcement
- TLS/HTTPS cipher support and verification
- HTTPS weak cipher and null cipher enforcement
- SNMPv3 version check and secure communications verification
- OEM-specific checks

---

## Device Profiles

Profiles define device-specific commands and expected outputs. They are stored as YAML and XLSX files under `icaf/profile/`.

- `default.yaml` / `default.xlsx` - Generic Linux target
- `alpine.yaml` / `alpine.xlsx` - Alpine Linux target
- `metasploitable.yaml` - Metasploitable test target

---

## Output

Test results and generated reports are written to the `output/` directory, which is created automatically on first run. Each clause execution produces a Word document report containing test results, evidence screenshots, and captured packet data.

---

## Logging

Logs are written to the `logs/` directory. The logger is configured in `icaf/utils/logger.py`.

---

## License

Refer to the project license file for terms of use.
