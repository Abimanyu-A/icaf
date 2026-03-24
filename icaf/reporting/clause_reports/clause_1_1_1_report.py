"""
reporting/clause_1_1_1.py
─────────────────────────────────────────────────────────────────────────────
Report generator for ITSAR 1.1.1 — Management Protocols Entity Mutual Auth.
WatchDog Router (WD4520-X1) | Apollo Infoways Private Limited

Key behaviours
──────────────
1. POSITION-AWARE NOT RUN detection
   Results are matched to YAML slots by runner_name → canonical → position.
   A slot is only marked RAN if its canonical name appears in the result map.
   If TC1 and TC5 ran but TC2/TC3/TC4 did not, the summary shows:
       TC1  PASS
       TC2  NOT RUN
       TC3  NOT RUN
       TC4  NOT RUN
       TC5  PASS
   No evidence from TC5 leaks into TC2/TC3/TC4's blocks.

2. AI-GENERATED OBSERVATION AND REMARKS (per TC)
   For every TC that actually ran, the generator calls the Anthropic
   /v1/messages API with:
     - the YAML spec description + steps + expected_result
     - the actual evidence (commands, outputs, screenshots list, status)
   The model writes a concise factual observation (~3 sentences) and a
   one-line remark. Falls back to YAML spec text if no evidence or API
   call fails.

3. PURPLE STYLE
   Uses the existing helpers from icaf.reporting.helpers — identical
   visual style to the original clause_1_1_1.py.

Entry point
───────────
    context = {
        'clause':     '1.1.1',
        'run_dir':    'output/runs/2026-03-13_10-10-42-1.1.1',
        'dut_info':   {...},
        'start_time': '13/03/2026',
        'end_time':   '13/03/2026',
    }
    results = [...]   # list of result dicts from runner

    path = Clause111Report(context, results).generate()
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
from typing import Any

import requests

from docx.shared import RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from icaf.reporting.helpers import (
    # colours
    PURPLE, LIGHT_PURPLE, DARK_GREY, MID_GREY,
    TABLE_HEADER_BG, TABLE_ALT_BG, PASS_GREEN, FAIL_RED, WHITE,
    NOT_RUN_COLOR, NOT_RUN_BG,
    HEX_PURPLE, HEX_PASS_GREEN, HEX_FAIL_RED,
    # low-level helpers
    _style_cell, _para_in_cell, _set_table_width, _set_col_widths,
    # paragraph builders
    section_heading, sub_heading, tc_heading,
    body_para, label_value_para, bullet_item, numbered_item,
    spacer, terminal_block, add_screenshot, status_result_table,
    # table builders
    two_col_info_table,
    # page-level builders
    build_front_page, build_doc_with_header_footer,
)
from icaf.reporting.spec_loader import load_clause_spec

logger = logging.getLogger(__name__)

# ── Anthropic API ─────────────────────────────────────────────────────────────
_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_MODEL   = "claude-sonnet-4-20250514"


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Unified dict/object accessor."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _clean_terminal_output(raw: str) -> list[str]:
    """
    Strip ANSI codes, leading/trailing blank lines.
    Cap at 40 lines to keep the document readable.
    """
    if not raw:
        return []
    ansi = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    text  = ansi.sub("", raw)
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return []
    if len(lines) > 40:
        lines = lines[:40] + [f"... [{len(lines) - 40} more lines truncated]"]
    return lines


def _summarise_evidence_for_ai(evidence: list[dict]) -> str:
    """
    Build a compact text block from evidence dicts so the AI has something
    concrete to write about.  Caps outputs at 30 lines each.
    """
    parts: list[str] = []
    for i, ev in enumerate(evidence, start=1):
        cmd  = ev.get("command")
        out  = ev.get("output")
        shot = ev.get("screenshot")
        block: list[str] = [f"--- Evidence block {i} ---"]
        if cmd:
            block.append(f"Command: {cmd}")
        if out:
            lines = _clean_terminal_output(out)[:30]
            block.append("Output:\n" + "\n".join(lines))
        if shot:
            fname = str(shot).split("/")[-1]
            block.append(f"Screenshot captured: {fname}")
        parts.append("\n".join(block))
    return "\n\n".join(parts) if parts else "(no evidence captured)"


# ─────────────────────────────────────────────────────────────────────────────
# AI observation / remark generator
# ─────────────────────────────────────────────────────────────────────────────

def _ai_generate_observation_and_remark(
    tc_name: str,
    spec: dict,
    result: dict,
) -> tuple[str, str]:
    """
    Call the Anthropic API to generate:
      • observation  — 2-4 factual sentences describing what actually happened
                       during the test, grounded in the evidence.
      • remark       — one concise sentence summarising the compliance outcome.

    Returns (observation, remark).  Falls back to YAML spec values on any
    error (network failure, missing API key, empty evidence, etc.).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # ── Fallback values from YAML ──────────────────────────────────────────
    yaml_obs    = spec.get("observation", "").strip()
    yaml_remark = spec.get("remarks",     "").strip()

    evidence = result.get("evidence") or []
    status   = result.get("status", "UNKNOWN").upper()

    # If there is no actual evidence at all, just use YAML text — there is
    # nothing for the model to reason about.
    has_real_evidence = any(
        ev.get("command") or ev.get("output") or ev.get("screenshot")
        for ev in evidence
    )
    if not has_real_evidence or not api_key:
        return yaml_obs or _default_observation(tc_name, status), \
               yaml_remark or _default_remark(tc_name, status)

    evidence_text   = _summarise_evidence_for_ai(evidence)
    description     = spec.get("description",     "").strip()
    steps           = spec.get("steps",           [])
    expected_result = spec.get("expected_result", "").strip()
    steps_text      = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))

    system_prompt = textwrap.dedent("""
        You are a security test report writer for ITSAR (Information Technology
        Security Assurance Requirements) evaluations.  Your job is to write
        factual, concise content for a formal test report based on the actual
        evidence from a test run.

        Rules:
        - Write ONLY what the evidence supports. Do NOT invent details.
        - Observation: 2–4 sentences. State what was observed during testing,
          referencing specific commands/outputs/Wireshark findings where present.
          End with whether the behaviour meets or does not meet ITSAR requirements.
        - Remark: exactly one sentence summarising the compliance outcome.
        - Use formal third-person technical language (no "I", no "we").
        - If status is PASS, confirm what was verified. If FAIL, state what failed.
        - Respond ONLY with valid JSON — no markdown fences, no preamble.
          Schema: {"observation": "...", "remark": "..."}
    """).strip()

    user_prompt = textwrap.dedent(f"""
        Test Case: {tc_name}
        Status: {status}

        Description:
        {description}

        Execution Steps:
        {steps_text}

        Expected Result:
        {expected_result}

        Actual Evidence Captured:
        {evidence_text}

        Write the observation and remark JSON now.
    """).strip()

    try:
        resp = requests.post(
            _ANTHROPIC_API_URL,
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model":      _ANTHROPIC_MODEL,
                "max_tokens": 512,
                "system":     system_prompt,
                "messages":   [{"role": "user", "content": user_prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw_text = resp.json()["content"][0]["text"].strip()

        # Strip any accidental markdown fences
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$",          "", raw_text)

        parsed = json.loads(raw_text)
        obs    = parsed.get("observation", "").strip()
        rem    = parsed.get("remark",      "").strip()

        if obs and rem:
            logger.debug("AI observation generated for %s", tc_name)
            return obs, rem

        # Partial result — fall back
        return (obs or yaml_obs or _default_observation(tc_name, status),
                rem or yaml_remark or _default_remark(tc_name, status))

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "AI observation generation failed for %s (%s) — using YAML fallback",
            tc_name, exc,
        )
        return (yaml_obs or _default_observation(tc_name, status),
                yaml_remark or _default_remark(tc_name, status))


def _default_observation(tc_name: str, status: str) -> str:
    if status == "PASS":
        return (
            f"The test case {tc_name} was executed and the DUT responded as expected. "
            "All verification steps were completed successfully. "
            "The behaviour observed meets the ITSAR security requirements."
        )
    return (
        f"The test case {tc_name} was executed but the DUT did not respond as expected. "
        "One or more verification steps failed during the test run. "
        "The observed behaviour does not meet the ITSAR security requirements."
    )


def _default_remark(tc_name: str, status: str) -> str:
    if status == "PASS":
        return f"The DUT correctly enforced the security requirement for {tc_name}."
    return f"The DUT failed to satisfy the security requirement for {tc_name}."


# ─────────────────────────────────────────────────────────────────────────────
# Main report class
# ─────────────────────────────────────────────────────────────────────────────

class Clause111Report:
    """Generates the full TCAF Word report for ITSAR clause 1.1.1."""

    def __init__(self, context: Any, results: list[dict]) -> None:
        self._ctx    = context
        self.results = list(results)
        self.spec    = load_clause_spec(self._ctx_get("clause", "1.1.1"))

        self.output_dir = (
            self._ctx_get("run_dir")
            or getattr(self._ctx_get("evidence", None), "run_dir", None)
            or "output"
        )

        # ── DUT metadata ─────────────────────────────────────────────────
        raw_info = self._ctx_get("dut_info") or {}
        di = raw_info if isinstance(raw_info, dict) else vars(raw_info)

        self.meta: dict[str, str] = {
            "dut_name":    (di.get("dut_name")
                            or self._ctx_get("dut_name")
                            or self._ctx_get("dut_model", "Device Under Test")),
            "dut_version": (di.get("dut_version")
                            or self._ctx_get("dut_version")
                            or self._ctx_get("dut_firmware", "N/A")),
            "os_hash":       di.get("os_hash",     "N/A"),
            "config_hash":   di.get("config_hash", "N/A"),
            "start_time":    self._ctx_get("start_time", "N/A"),
            "end_time":      self._ctx_get("end_time",   "N/A"),
            "itsar_id":      self._ctx_get("itsar_section", "1.1.1"),
            "itsar_version": "1.0.1",
        }

        # ── Build lookup tables from YAML ────────────────────────────────
        tc_specs = self.spec.get("testcases", {})
        # Ordered list of canonical names (YAML definition order)
        self._canonical_ordered: list[str] = list(tc_specs.keys())

        # runner_name → canonical  (and canonical → canonical for direct hits)
        self._runner_to_canonical: dict[str, str] = {}
        for canonical, tc_spec in tc_specs.items():
            runner_name = tc_spec.get("runner_name")
            if runner_name:
                self._runner_to_canonical[runner_name] = canonical
            self._runner_to_canonical[canonical] = canonical  # direct match

        # ── Build result_map: canonical → merged result ──────────────────
        #
        # CRITICAL: matching is done by name (runner_name lookup), NOT by
        # position in the results list.  This means:
        #   - TC1 and TC5 can run while TC2/TC3/TC4 stay NOT RUN.
        #   - Evidence from TC5 never leaks into TC2's slot.
        #
        self._result_map: dict[str, dict] = {}
        self._ran_canonical: list[str] = []  # ordered, deduped, names-only

        for pos, r in enumerate(self.results):
            runner_name = _get(r, "name", f"UNKNOWN_TC{pos+1}")
            canonical   = self._resolve_canonical(runner_name, pos)

            ev_new = _get(r, "evidence", []) or []

            if canonical in self._result_map:
                # Duplicate runner name — merge evidence, pessimistic status
                self._result_map[canonical]["evidence"].extend(ev_new)
                if _get(r, "status", "FAIL").upper() == "FAIL":
                    self._result_map[canonical]["status"] = "FAIL"
            else:
                self._result_map[canonical] = {
                    "name":        canonical,
                    "description": _get(r, "description", ""),
                    "status":      _get(r, "status", "FAIL").upper(),
                    "evidence":    list(ev_new),
                }
                self._ran_canonical.append(canonical)

        # ── Counters ─────────────────────────────────────────────────────
        ran_set = set(self._ran_canonical) & set(self._canonical_ordered)
        self._ran_count     = len(self._ran_canonical)
        self._total_defined = len(self._canonical_ordered)
        self._not_run_count = len(set(self._canonical_ordered) - ran_set)

        statuses = [self._result_map[n]["status"] for n in self._ran_canonical]
        self._pass_count = statuses.count("PASS")
        self._fail_count = len(statuses) - self._pass_count

        self.final_result = (
            "PASS"
            if self._fail_count == 0 and self._not_run_count == 0
            else "FAIL"
        )
        self.meta["final_result"] = self.final_result

        # ── Pre-generate AI observations for ran TCs ─────────────────────
        # Done once here so generate() is clean.
        tc_specs_dict = self.spec.get("testcases", {})
        self._ai_observations: dict[str, str] = {}
        self._ai_remarks:      dict[str, str] = {}

        for canonical in self._ran_canonical:
            result  = self._result_map[canonical]
            spec_tc = tc_specs_dict.get(canonical, {})
            obs, rem = _ai_generate_observation_and_remark(
                canonical, spec_tc, result
            )
            self._ai_observations[canonical] = obs
            self._ai_remarks[canonical]      = rem

    # ── Internal helpers ──────────────────────────────────────────────────

    def _ctx_get(self, key: str, default: Any = None) -> Any:
        if isinstance(self._ctx, dict):
            return self._ctx.get(key, default)
        return getattr(self._ctx, key, default)

    def _resolve_canonical(self, runner_name: str, position: int) -> str:
        """
        Resolve runner TC name → canonical YAML name.

        Priority:
          1. runner_name lookup (covers both direct and runner_name mappings)
          2. Position fallback (only if lookup misses — last resort)
        """
        if runner_name in self._runner_to_canonical:
            return self._runner_to_canonical[runner_name]
        # Position fallback — only kicks in for truly unknown names
        if position < len(self._canonical_ordered):
            logger.warning(
                "Runner name '%s' not found in spec — using position fallback "
                "(slot %d → %s)",
                runner_name, position, self._canonical_ordered[position],
            )
            return self._canonical_ordered[position]
        logger.warning(
            "Runner name '%s' not found in spec and position %d out of range — "
            "keeping runner name as-is",
            runner_name, position,
        )
        return runner_name

    # ── Section renderers ─────────────────────────────────────────────────

    def _section_revision_history(self, doc: Any) -> None:
        section_heading(doc, "Revision History")
        two_col_info_table(
            doc,
            headers    = ["Version", "Date",              "Changes"],
            col_widths = [1200,       1800,                6360],
            data_rows  = [
                ("V.1.0", "Initial Release",
                 "NCCS Approved Test Plan with initial Test Cases."),
                ("V.1.1", self.meta["start_time"],
                 "First Release of Test Report — automated evidence collected."),
            ],
        )

    def _section_preface(self, doc: Any) -> None:
        section_heading(doc, (
            "TSTR for Evaluation of 1.1 Management Protocols Entity "
            "Mutual Authentication (1.1.1 of CSR)"
        ))
        sub_heading(doc, "Preface")
        label_value_para(doc, "DUT Details", self.meta["dut_name"])
        spacer(doc)

        body_para(doc, "DUT Software Version:", bold=True)
        two_col_info_table(
            doc,
            headers    = ["Software Name",        "Software Version"],
            col_widths = [3600,                    5760],
            data_rows  = [("Device Firmware / OS", self.meta["dut_version"])],
        )
        spacer(doc)

        body_para(doc, "Digest Hash of OS:", bold=True)
        two_col_info_table(
            doc,
            headers    = ["Software Version",   "Hash Integrity Value"],
            col_widths = [3600,                   5760],
            data_rows  = [
                (self.meta["dut_version"], self.meta["os_hash"]),
                ("sshd_config",            self.meta["config_hash"]),
            ],
        )
        spacer(doc)

        body_para(doc, "Applicable ITSAR:", bold=True)
        for entry in self.spec["itsar"]["applicable_itsar"]:
            bullet_item(doc, f"{entry['ref']} ({entry['id']})")

        spacer(doc)
        body_para(doc, "ITSAR Version No.:", bold=True)
        for entry in self.spec["itsar"]["applicable_itsar"]:
            bullet_item(
                doc,
                f"{entry['version']} (Date of Release: {entry['release_date']})",
            )

    def _section_requirement(self, doc: Any) -> None:
        spacer(doc, large=True)
        itsar = self.spec["itsar"]
        body_para(
            doc,
            f"1. ITSAR Section No. & Name:  "
            f"{itsar['section_no']} {itsar['section_name']}",
            bold=True, color=PURPLE,
        )
        body_para(
            doc,
            f"2. Security Requirement No. & Name:  "
            f"{itsar['requirement_no']} {itsar['requirement_name']}",
            bold=True, color=PURPLE,
        )
        body_para(doc, "3. Requirement Description:", bold=True, color=PURPLE)
        body_para(doc, self.spec["requirement_description"].strip())

    def _section_dut_config(self, doc: Any) -> None:
        spacer(doc, large=True)
        body_para(doc, "4. DUT Configuration:", bold=True, color=PURPLE)
        body_para(
            doc,
            "Note: " + self.spec["dut_config"]["split_mode_note"].strip(),
        )
        spacer(doc)
        body_para(doc, "1) OAM Access supported by DUT:", bold=True)
        two_col_info_table(
            doc,
            headers    = ["Protocol", "Supported"],
            col_widths = [2800,        6560],
            data_rows  = [
                (row["protocol"], row["supported"])
                for row in self.spec["dut_config"]["oam_access"]
            ],
        )
        spacer(doc)
        body_para(doc, "NOTE:", bold=True, color=FAIL_RED)
        body_para(doc, self.spec["dut_config"]["snmp_note"].strip())

    def _section_preconditions(self, doc: Any) -> None:
        spacer(doc, large=True)
        body_para(doc, "5. Pre-conditions:", bold=True, color=PURPLE)
        for cond in self.spec["preconditions"]:
            bullet_item(doc, cond)

    def _section_test_objective(self, doc: Any) -> None:
        spacer(doc, large=True)
        body_para(doc, "6. Test Objective:", bold=True, color=PURPLE)
        bullet_item(doc, self.spec["test_objective"].strip())

    def _section_test_plan(self, doc: Any) -> None:
        spacer(doc, large=True)
        body_para(doc, "7. Test Plan:", bold=True, color=PURPLE)
        bullet_item(doc, self.spec["test_plan"]["scope_note"].strip())
        spacer(doc)

        sub_heading(doc, "a. Number of Test Scenarios:")
        for idx, (_, tc) in enumerate(
            self.spec["testcases"].items(), start=1
        ):
            numbered_item(doc, f"Test case {idx}: {tc['scenario']}")

        spacer(doc)
        sub_heading(doc, "b. Tools Required:")
        for tool in self.spec["test_plan"]["tools"]:
            bullet_item(doc, tool)

        spacer(doc)
        body_para(
            doc, "8. Expected Results for Pass:", bold=True, color=PURPLE
        )
        for idx, (_, tc) in enumerate(
            self.spec["testcases"].items(), start=1
        ):
            numbered_item(
                doc, f"Test case {idx}: {tc['expected_result']}"
            )

        spacer(doc)
        body_para(
            doc, "9. Expected Format of Evidence:", bold=True, color=PURPLE
        )
        body_para(doc, self.spec["test_plan"]["evidence_format"].strip())

    # ── Test execution section ─────────────────────────────────────────────

    def _section_test_execution(self, doc: Any) -> None:
        doc.add_page_break()
        section_heading(doc, "10. Test Execution")

        if self._not_run_count > 0:
            spacer(doc, small=True)
            body_para(
                doc,
                f"NOTE: This report covers {self._ran_count} of "
                f"{self._total_defined} defined test cases. "
                f"{self._not_run_count} case(s) were not executed in this run.",
                bold=True, color=FAIL_RED,
            )

        tc_specs = self.spec.get("testcases", {})

        # ── Iterate YAML order — only render TCs that actually ran ────────
        # This is the core of the position-aware logic:
        #   • We walk the CANONICAL YAML order, not the results list.
        #   • We only emit a full block for TCs whose canonical name is in
        #     self._result_map (i.e. they actually ran).
        #   • NOT RUN slots are skipped here — they appear in the summary
        #     table (section 11) but NOT in the execution section.
        #     This prevents any evidence bleed-over.

        rendered_idx = 0
        for canonical in self._canonical_ordered:
            if canonical not in self._result_map:
                # TC was not run — skip it in execution section
                continue

            rendered_idx += 1
            result = self._result_map[canonical]
            spec   = tc_specs.get(canonical, {})

            spacer(doc)
            tc_heading(doc, f"{rendered_idx}. Test Case Name: {canonical}")
            spacer(doc, small=True)

            # a. Description
            sub_heading(doc, "a. Test Case Description:")
            desc = (spec.get("description") or result.get("description") or "").strip()
            body_para(doc, desc or "No description available.")
            spacer(doc)

            # b. Execution steps (from YAML — runner always sends [])
            steps = spec.get("steps", [])
            if steps:
                sub_heading(doc, "b. Execution Steps:")
                for step in steps:
                    numbered_item(doc, step)
                spacer(doc)

            # c. Evidence
            evidence = result.get("evidence") or []
            has_ev   = any(
                ev.get("command") or ev.get("output") or ev.get("screenshot")
                for ev in evidence
            )

            if has_ev:
                sub_heading(doc, "c. Evidence Captured:")
                for ev in evidence:
                    command    = ev.get("command")
                    output_raw = ev.get("output")
                    screenshot = ev.get("screenshot")

                    if command:
                        label_value_para(doc, "Command Executed", command)

                    if output_raw:
                        lines = _clean_terminal_output(output_raw)
                        if lines:
                            body_para(doc, "Command Output:", bold=True)
                            terminal_block(doc, lines)
                            spacer(doc, small=True)

                    if screenshot:
                        from icaf.reporting.helpers import _resolve_screenshot_path
                        clean_path = _resolve_screenshot_path(screenshot)
                        if clean_path:
                            body_para(
                                doc,
                                f"Evidence Screenshot — "
                                f"{os.path.basename(clean_path)}",
                                bold=True,
                            )
                            add_screenshot(doc, clean_path, width_inches=5.5)
                            spacer(doc, small=True)
                        else:
                            fname = str(screenshot).split("/")[-1]
                            body_para(
                                doc,
                                f"Screenshot captured: {fname} "
                                f"(file path recorded; attach manually if required)",
                                italic=True, color=MID_GREY,
                            )
                spacer(doc)

            # d. Observations — AI-generated (or YAML fallback)
            sub_heading(doc, "d. Test Observations:")
            observation = self._ai_observations.get(canonical, "")
            body_para(
                doc,
                observation or "Observation recorded during test execution.",
            )
            spacer(doc, small=True)

            # e. Evidence statement
            sub_heading(doc, "e. Evidence Provided:")
            body_para(
                doc,
                "Screenshots and command outputs are captured and attached "
                "during testing. Automated evidence is embedded above.",
            )
            spacer(doc, small=True)

            # Result badge
            status_result_table(doc, result["status"])

            spacer(doc, large=True)
            _add_divider(doc)
            spacer(doc, large=True)

    # ── Result summary section ─────────────────────────────────────────────

    def _section_result_summary(self, doc: Any) -> None:
        doc.add_page_break()
        section_heading(doc, "11. Test Case Result Summary")
        spacer(doc)

        tc_specs   = self.spec.get("testcases", {})
        headers    = ["SL No.", "Test Case Name", "Result", "Remarks"]
        col_widths = [720, 3840, 1200, 3600]

        # ── Walk YAML order — every TC appears; ran ones get real status ──
        data_rows: list[tuple] = []
        for sl, canonical in enumerate(self._canonical_ordered, start=1):
            spec = tc_specs.get(canonical, {})

            if canonical in self._result_map:
                r      = self._result_map[canonical]
                status = r["status"]
                # Use AI-generated remark if available, else YAML
                remarks = (
                    self._ai_remarks.get(canonical)
                    or spec.get("remarks", "")
                )
            else:
                status  = "NOT RUN"
                remarks = "Test case was not executed in this run."

            data_rows.append((str(sl), canonical, status, remarks, status))

        totals_detail = (
            "All test cases passed successfully."
            if self.final_result == "PASS"
            else (
                f"{self._fail_count} case(s) failed"
                + (
                    f", {self._not_run_count} not run."
                    if self._not_run_count
                    else "."
                )
            )
        )
        counts_str = f"{self._pass_count}P / {self._fail_count}F"
        if self._not_run_count:
            counts_str += f" / {self._not_run_count}NR"

        totals_row = (
            "",
            f"Total: {self._total_defined} defined  |  {self._ran_count} ran",
            counts_str,
            totals_detail,
            self.final_result,
        )
        _build_summary_table(doc, headers, col_widths, data_rows, totals_row)

    # ── Conclusion section ────────────────────────────────────────────────

    def _section_conclusion(self, doc: Any) -> None:
        spacer(doc, large=True)
        section_heading(doc, "12. Test Conclusion")
        spacer(doc)

        for b in self.spec.get("conclusion_bullets", []):
            bullet_item(doc, b)

        if self._not_run_count > 0:
            bullet_item(
                doc,
                f"NOTE: This run executed {self._ran_count} of "
                f"{self._total_defined} defined test cases. The remaining "
                f"{self._not_run_count} case(s) were not run and must be "
                f"completed before a final pass verdict can be issued.",
                bold=True,
            )

        spacer(doc)
        status_result_table(
            doc,
            status=self.final_result,
            label="Overall Evaluation Result",
            detail=(
                f"{self._pass_count} of {self._total_defined} cases passed."
                if not self._not_run_count
                else (
                    f"{self._pass_count} passed, "
                    f"{self._fail_count} failed, "
                    f"{self._not_run_count} not run."
                )
            ),
            wide=True,
        )

    # ── Entry point ───────────────────────────────────────────────────────

    def generate(self) -> str:
        """
        Build and save <run_dir>/tcaf_report.docx.
        Returns the absolute path to the saved file.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        report_path = os.path.join(self.output_dir, "tcaf_report.docx")

        doc = build_doc_with_header_footer(
            dut_name    = self.meta["dut_name"],
            dut_version = self.meta["dut_version"],
        )

        build_front_page(doc, self.meta)
        doc.add_page_break()

        self._section_revision_history(doc)
        doc.add_page_break()

        self._section_preface(doc)
        self._section_requirement(doc)
        self._section_dut_config(doc)
        self._section_preconditions(doc)
        self._section_test_objective(doc)
        self._section_test_plan(doc)

        self._section_test_execution(doc)
        self._section_result_summary(doc)
        self._section_conclusion(doc)

        doc.save(report_path)
        logger.info("Report saved: %s", report_path)
        return report_path


# ─────────────────────────────────────────────────────────────────────────────
# Module-private document helpers
# ─────────────────────────────────────────────────────────────────────────────

def _add_divider(doc: Any) -> None:
    """Thin grey horizontal rule between test case blocks."""
    p    = doc.add_paragraph()
    pPr  = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot  = OxmlElement("w:bottom")
    bot.set(qn("w:val"),   "single")
    bot.set(qn("w:sz"),    "4")
    bot.set(qn("w:color"), "DDDDDD")
    pBdr.append(bot)
    pPr.append(pBdr)


def _build_summary_table(
    doc:        Any,
    headers:    list[str],
    col_widths: list[int],
    data_rows:  list[tuple],
    totals_row: tuple,
) -> None:
    """
    Result summary table.

    data_rows   list of 5-tuples:
                  (sl_str, canonical_name, status_text, remarks, status_key)
                  status_key → "PASS" | "FAIL" | "NOT RUN"

    totals_row  5-tuple:
                  (sl_empty, summary_str, counts_str, remark_str, final_key)
    """
    from docx.enum.table import WD_TABLE_ALIGNMENT

    table = doc.add_table(rows=0, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    _set_table_width(table, sum(col_widths))
    _set_col_widths(table, col_widths)

    # Header row
    hdr = table.add_row()
    for ci, (h, w) in enumerate(zip(headers, col_widths)):
        c = hdr.cells[ci]
        _style_cell(c, TABLE_HEADER_BG, HEX_PURPLE, w)
        _para_in_cell(c, h, bold=True, color=WHITE, center=True)

    # Data rows
    for ri, (sl, tc_name, status_text, remarks, status_key) in enumerate(
        data_rows
    ):
        row    = table.add_row()
        row_bg = TABLE_ALT_BG if ri % 2 else "FFFFFF"
        sk     = status_key.upper()

        if sk == "PASS":
            s_bg = "E8F5E9"
            s_col = RGBColor(0x00, 0x64, 0x00)
        elif sk == "NOT RUN":
            s_bg  = NOT_RUN_BG
            s_col = NOT_RUN_COLOR
        else:   # FAIL
            s_bg  = "FFEBEE"
            s_col = RGBColor(0xCC, 0x00, 0x00)

        for ci, (val, w) in enumerate(
            zip([sl, tc_name, status_text, remarks], col_widths)
        ):
            c = row.cells[ci]
            if ci == 2:   # status column — colour-coded
                _style_cell(c, s_bg, "CCCCCC", w)
                _para_in_cell(c, val, bold=True, color=s_col, center=True)
            else:
                _style_cell(c, row_bg, "CCCCCC", w)
                _para_in_cell(
                    c, val, color=DARK_GREY, center=(ci == 0)
                )

    # Totals row
    tot    = table.add_row()
    fk     = totals_row[4].upper()
    tot_col = (
        RGBColor(0x00, 0x64, 0x00) if fk == "PASS"
        else RGBColor(0xCC, 0x00, 0x00)
    )
    for ci, (val, w) in enumerate(zip(totals_row[:4], col_widths)):
        c = tot.cells[ci]
        _style_cell(c, LIGHT_PURPLE, "CCCCCC", w)
        _para_in_cell(
            c, val, bold=True, color=tot_col, center=(ci in (0, 2))
        )