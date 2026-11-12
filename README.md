# Less Scaffold, Same Fixes? (Gemma 4 Developer Agent Paper Track)

Code and raw results for the Kaggle Writeup by Shyam (Sam) Desigan, Cubiczan. See `PAPER.md`.

| Path | What it is |
|---|---|
| `submission/` | Config A: fixer, localizer (AgentTool) and `python-bugfix-playbook` skill |
| `ablation_single/` | Config B: same fixer prompt, single agent |
| `submission_fixed/` | Config C: lean two-agent variant (4.5 min, 4,096 tokens, no skill) |
| `submission_minimal/` | Config D: lean single-agent variant |
| `submission_e4b/` | E4B variant (declares an alias missing from the released registry; see paper, finding 5) |
| `validate.py`, `scorer_check.py` | Compile a submission or zip via the official `adk_submission` 0.2.11 / `swegemma` 0.2.7 path |
| `localeval/` | Proxy harness (`run_agent.py`, `env.py`), task miner (`mk_tasks.py`), 7 verified rich tasks (`tasks.jsonl`), per-run results with tool-call traces (`res_*.jsonl`) |

The checks expect the organizers' released `adk_submission`, `adk_eval_core` and `swegemma` packages on `PYTHONPATH` (`../official_harness_ref`) and `google-adk`. The proxy runs in the paper used gpt-4.1-mini (the `PROXY_MODEL` default) over the OpenAI API. `run_agent.py` reads the model, endpoint and API key variable name from `PROXY_MODEL`, `PROXY_BASE` and `PROXY_KEYVAR`; no keys are included. Task data is derived from Textualize/rich (MIT).

License: Apache-2.0.
