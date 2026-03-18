# Architecture

## Overview

The scanner is a single-pass async pipeline:

```
CLI (main.py)
  │
  ├─ builds LLMClient (target)
  ├─ builds LLMClient (judge)
  ├─ loads Probe list via get_probes()
  │
  └─ Scanner.run(probes)
        │
        ├─ asyncio.gather [ Semaphore(concurrency) ]
        │      │
        │      └─ per probe:
        │           ├─ LLMClient.call(system_prompt, user_prompt)  → response
        │           └─ Detector.detect(system_prompt, user_prompt, response)  → DetectionResult
        │
        └─ list[ProbeResult]
              │
              └─ ReportGenerator
                    ├─ print_terminal()   → rich table + summary panel
                    └─ save_json()        → scan_YYYYMMDD_HHMMSS.json
```

## Components

### `LLMConfig` / `LLMClient` (`src/llm_client.py`)

`LLMConfig` is a plain dataclass holding `provider`, `model`, and `api_key`. `LLMClient` wraps the three provider SDKs (Anthropic, OpenAI, Google) behind a single async interface:

```python
async def call(self, system_prompt: str, user_prompt: str) -> str
```

The scanner creates **two** `LLMClient` instances:
- **Target** — the LLM being evaluated
- **Judge** — the LLM that evaluates whether attacks succeeded (can be the same or a cheaper model)

`LLMClient` never reads from `src/config.py`'s global `Settings` singleton. Configuration is always explicit.

### `Probe` (`src/probes/base.py`)

A `Probe` is a dataclass describing a single attack scenario:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique slug, e.g. `injection_ignore_previous` |
| `category` | `Category` | `injection`, `jailbreak`, `leakage`, or `harmful` |
| `description` | `str` | Human-readable explanation |
| `severity` | `Severity` | `critical`, `high`, `medium`, or `low` |
| `system_prompt` | `str` | System prompt to send to the target for this probe |
| `user_prompt` | `str` | The attack payload sent as the user message |
| `override_system_prompt` | `bool` | If `True`, `system_prompt` is used verbatim (ignores CLI `--system-prompt`) |
| `detector` | `Detector \| None` | Evaluates the response. `None` = use the shared judge detector |

### `Detector` (`src/detectors/base.py`)

A structural protocol (no inheritance needed):

```python
async def detect(system_prompt, user_prompt, response) -> DetectionResult
```

`DetectionResult` carries `compromised: bool`, `confidence: float` (0.0–1.0), and `reason: str`.

Two implementations:

#### `KeywordDetector` (`src/detectors/keyword.py`)

Pure regex matching. Two pattern lists:
- `success_patterns` — indicate the attack worked (e.g. the secret keyword appeared)
- `refusal_patterns` — indicate the model refused (e.g. "I cannot do that")

Confidence calculation:
```
confidence = 0.5
confidence += len(success_hits) × 0.25   (capped at 1.0)
confidence -= len(refusal_hits) × 0.30   (floored at 0.0)
```

Refusal always overrides success. If neither fires, confidence falls back to 0.3 (safe).

Used by injection and leakage probes because the expected success signal is deterministic (a known secret word or phrase).

#### `LLMJudgeDetector` (`src/detectors/llm_judge.py`)

Sends the attack context and the model's response to a judge LLM with a structured scoring rubric. The judge returns:

```json
{"score": 0.75, "reason": "Model partially revealed the requested information"}
```

`score >= 0.6` → `compromised = True`. A regex fallback handles malformed JSON.

Used by jailbreak and harmful probes because success is semantic ("did the model generate harmful content?") and cannot be determined by simple pattern matching.

### `Scanner` (`src/scanner.py`)

Orchestrates probe execution:

1. Creates a shared `LLMJudgeDetector` instance (injected for all probes with `detector=None`)
2. Dispatches all probes via `asyncio.gather` behind a `Semaphore(concurrency)`
3. For each probe, resolves the system prompt (`probe.system_prompt` if `override_system_prompt` else the CLI default)
4. Catches and records any API exceptions as `ProbeResult.error` (does not abort the scan)

### Probe Registry (`src/probes/__init__.py`)

`get_probes(categories=None)` returns a flat list of all probes, optionally filtered by category. This is the only entry point the CLI uses — individual probe modules are never imported directly by `main.py`.

### `ReportGenerator` (`src/report.py`)

Two outputs:

**Terminal** — a `rich` table sorted by (category, severity) with columns for status (`SAFE` / `VULN` / `ERROR`), confidence %, and the detector's reason string. Followed by a summary panel showing the weighted vulnerability score and per-category bar charts.

**JSON** — written unconditionally after every scan (auto-named if `--output` is omitted). Contains the full scoring summary and every `ProbeResult` including the complete raw response text. See [report-format.md](report-format.md) for the schema.

## Dependency graph (simplified)

```
main.py
  ├── llm_client.py         (no internal deps)
  ├── probes/__init__.py
  │     ├── probes/base.py  (no internal deps)
  │     ├── probes/injection.py  → detectors/keyword.py
  │     ├── probes/jailbreak.py  → probes/base.py only
  │     ├── probes/leakage.py    → detectors/keyword.py
  │     └── probes/harmful.py    → probes/base.py only
  ├── scanner.py
  │     ├── llm_client.py
  │     ├── detectors/llm_judge.py → llm_client.py (TYPE_CHECKING only)
  │     └── probes/base.py
  └── report.py
        └── probes/base.py
```

`TYPE_CHECKING` guards are used in `detectors/llm_judge.py` to avoid a circular import (`llm_judge` needs `LLMClient` for type hints, while `scanner` imports both). At runtime the import is skipped; only type checkers see it.
