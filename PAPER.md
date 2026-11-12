# Less Scaffold, Same Fixes? Delegation, Skills and Harness Fidelity for Budget-Bound Gemma 4 Coding Agents

**Subtitle:** A localize-reproduce-patch-verify agent written in ADK Agent Config, a local proxy built on the organizers' own compiler, and a 42-run ablation in which optional sub-agents and skills were almost never used.

**Author:** Shyam (Sam) Desigan, Cubiczan

## Abstract

The Gemma 4 Developer Agent Competition fixes the model and the hardware. Every agent runs one Gemma 4 checkpoint with a 32k context and no network, and about 120 SWE-bench-style tasks must finish inside a hard 12-hour cap. Competitors can only change a declarative Google ADK configuration: prompts, sampling, sub-agents, skills and LoRA adapters. This paper reports three things.

1. **An agent.** A *fixer* runs a localize, reproduce, patch, verify, submit loop. A read-only *localizer* is exposed as an `AgentTool`, so its exploration never enters the fixer's context, and an ADK skill holds bug-pattern checklists.
2. **A local evaluation proxy.** It compiles each submission with the organizers' own `adk_submission` 0.2.11 compiler and mirrors the harness's tool limits, prompt and fail-to-pass verification.
3. **A controlled ablation** of four configurations, 42 runs in total, on 7 verified tasks mined from Textualize/rich.

Configurations that offered the localizer resolved 7/21 runs (33.3%), and single-agent configurations resolved 9/21 (42.9%). The difference is within noise. The fixer called the localizer in 1 of 21 runs and never loaded the skill in 28 runs where the skill was available. Outcome was set almost entirely by the task: three tasks accounted for every success, and four were never solved under any configuration. Under tight per-task budgets, optional delegation is mostly ignored. Scaffolding has to be *forced* (workflow agents) or *trained in* (LoRA) to matter. We also report five compiler and harness behaviours, each re-checked against the released code, that silently change agent behaviour or invalidate a submission.

**Scope note.** The agent loop in Section 5 ran on an OpenAI-compatible proxy model, not on Gemma 4, because we had no Gemma 4 serving available during development. All configurations target Gemma 4 and compile against the official registry (Section 6). The proxy numbers support comparisons between configurations, not leaderboard predictions.

## 1. Introduction

Most coding-agent results assume a frontier API model with a generous context and a generous wall-clock budget. This competition inverts that. The model is a 4-bit Gemma 4 checkpoint, the context is 32,768 tokens, and the whole test set has to finish within 12 hours. That clock includes sandbox setup and vLLM start-up.

With about 120 tasks run sequentially and roughly 1.5-2 minutes of per-task harness overhead reported by other participants, the agent gets about **3.5 minutes per task**. That is 20 to 40 tool calls.

These constraints change which design choices matter. Multi-agent decomposition (planner, localizer, editor, verifier) is attractive because sub-agents isolate context. But every delegated call spends time from the same budget, and the root model decides whether to delegate at all. We ask two questions:

1. Does an optional read-only localizer sub-agent plus a skill help a budget-bound coding agent, compared with a single agent given the same instructions?
2. Which harness behaviours must a local evaluation proxy reproduce to make such comparisons trustworthy?

**Contributions.**
- A declarative two-agent, one-skill agent configuration, plus three variants, all validated against the official `adk_submission` 0.2.11 compiler and the `swegemma` 0.2.7 pre-run path.
- A lightweight local proxy harness of about 250 lines. It compiles the *actual* submission zip with the official compiler, re-implements the harness tools with the documented limits, and verifies patches with the fail-to-pass protocol.
- A controlled ablation with per-run traces, and five harness-fidelity findings useful to anyone building on ADK Agent Config.

## 2. Setting

**Tools.** The harness exposes these tools:
- `run_command`
- `read_file` (150 lines or 10k characters)
- `edit_file` (exact string replacement)
- `write_file`
- `get_status`
- `submit_patch` (`git add -N . && git diff HEAD`)
- three graph tools over precomputed AST call graphs and 256-d node embeddings: `search_similar_code`, `get_code_neighbors` and `get_code_subgraph`

**Scoring.** The agent's diff is applied in a fresh container. Test files touched by the hidden `test_patch` are reset, the test patch is applied, and the targeted pytest run must exit 0.

**Submission.** A zip whose root `agent.yaml` is compiled into an ADK agent tree. Only YAML, Markdown, `.py` skill scripts, adapter JSON and safetensors files are allowed, and every agent must declare the same base model.

## 3. Method

### 3.1 Fixer (root agent)
The fixer is a single `LlmAgent` with all edit and run tools. It runs at temperature 0.6 with up to 6,144 output tokens and thinking disabled (Section 6, finding 1). Its instruction prescribes a five-phase loop with explicit call budgets:

1. **Localize (1-4 calls).** Extract anchors (error strings, symbols, parameter names) and grep for them. Use `search_similar_code` for concepts and `get_code_neighbors` to expand from a known symbol. Delegate to the localizer if the location is still unclear after two searches.
2. **Reproduce (optional, at most 2 calls).** Write a short script in `/tmp`, never in `/workspace`, because untracked files there leak into the patch.
3. **Patch.** Make minimal `edit_file` changes with short, unique anchors. Keep public signatures backward compatible (new keyword arguments get defaults). Never touch tests, `pytest.ini` or `conftest.py`.
4. **Verify.** Re-run the repro and the closest existing test file, then check `git status`.
5. **Submit.** Always call `submit_patch`, even when unsure, and immediately when less than about 60 seconds remain.

### 3.2 Localizer (AgentTool)
The localizer is a read-only `LlmAgent` with the graph tools, `read_file` and `run_command`. It uses `include_contents: none` and a scout sampling config: temperature 0.3, 2,048 tokens, thinking off. It is wrapped as an `agent_tool`.

It must answer in a fixed format:
- up to three `file:line-range symbol - reason` entries
- the related test file
- a one-sentence root cause

Its file reads therefore never enter the fixer's 32k context. ADK compaction only triggers at the full window, so this isolation is the main defence against running out of context.

### 3.3 Skill
`python-bugfix-playbook` is an ADK skill with two Markdown resources:
- symptom-to-root-cause checklists: threading a new option through sync and async paths, `None` versus falsy checks, union-type handling, header and encoding defaults, and cell-width rendering
- a checklist for verification and diff hygiene

Skills load lazily via `load_skill_resource`, so they cost context only when used.

### 3.4 Budget configuration
`eval_config.yaml` sets 3.5 minutes, 40 tool calls, 80 turns and a 180-second command timeout. With 1.5-2 minutes of overhead per task, 120 tasks need about 10-11 hours, which leaves margin under the 12-hour cap. Exceeding the cap fails the whole submission.

## 4. Local proxy harness

The competition's 129 public tasks (fastapi, rich, requests and httpx) are distributed through Kaggle. To iterate offline and to have tasks with fully known provenance, we built our own tasks with the organizers' published curation recipe.

- **Mining.** We took merge commits of Textualize/rich since 2024 whose diff touches 1-2 library files under `rich/` and at least one `tests/test_*.py` file. The problem statement is the linked issue's title and body, or the PR description if no issue is linked. `patch` is the library diff and `test_patch` is the test diff.
- **Task verification.** Each candidate must pass with the gold patch and fail without it. All 8 candidates passed with the gold patch. One (rich#3937) also passed *without* it in our environment and was dropped. That leaves **7 tasks**: rich#3718, #3882, #3894, #3905, #3935, #4006 and #4075. Task #4006 is an infinite-loop bug: without a fix, its tests hang until the verifier timeout and count as failures.
- **Agent run.** The submission directory is compiled with the official `compile_submission` and `build_submission_limits`, with no reimplementation of the config language. The tools re-implement the documented signatures and limits:
  - 5,000-character command output and 150-line reads
  - call and time gating that returns a "budget exhausted" error
  - `submit_patch` as `git add -N` plus `git diff HEAD`

  The initial user message follows the documented `build_agent_prompt` sections. Up to three continuation nudges are sent when a turn ends without a tool call.
- **Patch verification.** The patch is applied in a fresh copy (`git apply`, then `-3`, then `patch -p1`). Target test files are reset and the test patch is applied. A task counts as resolved when pytest exits with code 0.
- **Known deviations.**
  - The graph tools are approximated by an AST symbol index with lexical similarity, because the competition's precomputed graphs and embeddings were not part of our task set.
  - The proxy runs as a host subprocess, not in Docker.
  - The model is an OpenAI-compatible proxy (gpt-4.1-mini), not Gemma 4, so vLLM-specific thinking settings are stripped (Section 6, finding 4).

  Absolute success rates are therefore **not** predictive of leaderboard scores. Only comparisons within the proxy are meaningful.

## 5. Experiments

### 5.1 Configurations
All four configurations declare `gemma-4-31b-it-qat-w4a16-ct`, a 40-call cap and the same tool set, and all compile on the official pre-run path.

- **A, Two-agent** (2 repeats): fixer, localizer (`skip_summarization: true`) and skill, with a 3.5-minute budget and 6,144 output tokens.
- **B, Single** (2 repeats): the identical fixer prompt with the two lines that mention the localizer and skill removed. It has the same tools minus the localizer, no skill, and the same budget and sampling as A.
- **C, Two-agent, lean** (1 repeat): fixer plus localizer (`skip_summarization: false`), with no skill, 4,096 output tokens and a 4.5-minute budget.
- **D, Single, lean** (1 repeat): C's fixer prompt without the localizer line, with the same 4,096-token and 4.5-minute settings.

C and D were built as smaller, cheaper main-track candidates. They also give a second, independent A-versus-B style comparison.

### 5.2 Results
All results were measured with the proxy model on 7 tasks.

| Config | Resolved | Rate | Mean tool calls | Median wall time | Runs at 40-call cap | Empty patch | Localizer used | Skill used | Runs that ran pytest |
|---|---|---|---|---|---|---|---|---|---|
| A Two-agent | 5/14 | 35.7% | 22.0 | 18 s | 2 | 2 | 1/14 | 0/14 | 12/14 |
| B Single | 6/14 | 42.9% | 20.9 | 21 s | 3 | 2 | n/a | n/a | 12/14 |
| C Two-agent, lean | 2/7 | 28.6% | 18.0 | 22 s | 0 | 0 | 0/7 | n/a | 7/7 |
| D Single, lean | 3/7 | 42.9% | 28.9 | 22 s | 2 | 2 | n/a | n/a | 5/7 |
| **With localizer (A+C)** | **7/21** | **33.3%** | | | | | **1/21** | 0/14 | |
| **Without (B+D)** | **9/21** | **42.9%** | | | | | | | |

Patches that were not empty were small: the median was 15 lines in A, B and C, and 13 in D. Every run except one called `submit_patch` explicitly. Wall time was not binding: no run used more than 61 s, so the **call cap**, not the clock, was the active budget for this proxy.

| Task | Solved (all 42 runs) |
|---|---|
| rich#3882 | 6/6 |
| rich#3905 | 6/6 |
| rich#3894 | 4/6 (A 1/2, B 2/2, C 0/1, D 1/1) |
| rich#3718, #3935, #4006, #4075 | 0/6 each |

### 5.3 Analysis
**Configuration effects are within noise.** Every difference between configurations comes from one task, #3894. A two-sided Fisher exact test on 7/21 versus 9/21 gives p ≈ 0.75. We do **not** claim that the single agent is better.

**Delegation is optional, so it is skipped.** Across 21 runs in which the localizer was available, the fixer delegated once. That was a failed #3894 run that spent 33 calls. Across 14 runs with the skill available, it never loaded a resource. The model preferred direct `grep` and `read_file`, which is the cheapest path under a call cap. This held with summarization on and off (C versus A), and with both the 3.5-minute and 4.5-minute budgets.

**Failures look like budget exhaustion, not crashes.** The hardest tasks (#4006, an infinite loop, and #4075) repeatedly reached 38-43 calls. All six empty patches came from runs that ended at 41-43 calls without a surviving edit. Five runs hit a malformed JSON tool argument from the model (`Unterminated string`), and each continued after a nudge. One of those runs still solved its task.

**Implication.** Extra scaffolding that the model is free to ignore adds prompt tokens and compile-time risk without changing behaviour. To test scaffolding properly, it must be mandatory. One way is a `SequentialAgent` of localizer, then fixer, then verifier, passing the localizer output via `output_key`. Another is a LoRA fine-tuned on trajectories that include delegation. Both are allowed by the submission format.

## 6. Harness-fidelity findings

We re-ran each check on Nov 12, 2026, by compiling modified submission zips through a script that reproduces the scorer's pre-run and per-task compile path using the released `swegemma` 0.2.7 and `adk_submission` 0.2.11 sources.

1. **`include_thoughts: false` disables thinking entirely.** The generation resolver maps `include_thoughts: false`, `thinking_level: NONE` or a non-positive budget to `chat_template_kwargs.enable_thinking=false`, whatever `thinking_budget` says. A config with `thinking_budget: 1024, include_thoughts: false` compiled to `enable_thinking: False`. The same config without `include_thoughts` compiled to `enable_thinking: True`. To get budgeted thinking, omit `include_thoughts`.
2. **Skill names must be kebab-case.** Renaming our skill's `SKILL.md` frontmatter name to `python_bugfix_playbook` fails compilation with a pydantic validation error. On the scorer, that means a failed daily submission.
3. **`!include` is sandboxed to the submission root, not to the including file's directory.** Paths resolve relative to the including file, then must stay inside the zip root, and symlinks are rejected. Variant C's sub-agent includes `../prompts/localizer.md` and compiles cleanly. An earlier draft of this paper claimed that `..` was forbidden; that was wrong. Only escaping the root fails.
4. **Thinking config leaks vendor keyword arguments.** Thinking is bridged through vLLM-specific `extra_body.chat_template_kwargs`, so the same config fails against generic OpenAI-compatible endpoints. Local proxies must strip it, and results with thinking cannot be reproduced on endpoints other than vLLM.
5. **The QAT E4B alias is not in the released model registry.** The registry built by `setup_gemma_model_registry` lists `gemma-4-e4b-it` and `gemma-4-31b-it-qat-w4a16-ct`, but not `gemma-4-e4b-it-qat-w4a16-ct`. Our E4B variant, which declared the QAT name by analogy with the 31B model, fails with `ModelNotFoundError` before any task runs. Entrants targeting the small-model prize should use an alias that the registry actually lists.

We also confirm the documented diff-hygiene hazard: scratch files under `/workspace` enter the patch. Our prompt routes all repro scripts to `/tmp`.

## 7. Related work

- SWE-bench [1] introduced repository-level issue resolution with fail-to-pass test verification, and SWE-bench Lite and Verified are its common subsets.
- SWE-agent [2] showed that agent-computer interface design, such as windowed file viewers and concise edit commands, strongly affects success. This competition's harness inherits that design (150-line reads, string-replacement edits).
- Agentless [3] showed that a fixed localize, repair, validate pipeline without free-form agency is competitive. That motivates the forced `SequentialAgent` variant we propose.
- AutoCodeRover [4] and RepoGraph [5] use program structure, such as AST search and repository graphs, for localization. That is the role of the competition's graph tools and of our localizer.
- OpenHands [6] provides a general multi-agent platform with delegation.
- SWE-Gym [7] and SWE-smith [8] train open models on agent trajectories. That is the natural next step (a LoRA) for making scaffolding behaviours reliable in small models.
- Google ADK [9] defines the Agent Config format used here.

## 8. Limitations and next steps

**Limitations.**
- The task set is small (7 tasks from 1 repository), and C and D have one repeat each.
- The agent model is a proxy, not Gemma 4. Gemma 4 31B at 4 bits may delegate more or less readily, and its tool-call formatting errors may differ.
- The graph tools are approximated, and the proxy does not reproduce container resource limits or vLLM latency, so the 3.5-minute clock was never binding here.

**Next steps.**
- Run A-D with Gemma 4 31B and E4B on vLLM over the 129 public tasks.
- Add the forced localize, patch, verify workflow.
- Distill successful trajectories into a rank-16 LoRA for the fixer, which fits well within the 3 GiB limit.
- Measure the 12-hour budget arithmetic on the real scorer.

## Reproducibility

- **Configs:** `submission/` (A), `ablation_single/` (B), `submission_fixed/` (C), `submission_minimal/` (D) and `submission_e4b/`.
- **Checks:** `validate.py` and `scorer_check.py` (the official compile path).
- **Proxy harness and tasks:** `localeval/mk_tasks.py`, `env.py`, `run_agent.py` and `tasks.jsonl`.
- **Raw per-run results with full tool-call traces:** `localeval/res_*.jsonl`.

Code, configs, tasks and raw results: https://github.com/Cubiczan/gemma4-agent-paper (Apache-2.0).

## References

[1] C. E. Jimenez et al. SWE-bench: Can Language Models Resolve Real-World GitHub Issues? ICLR 2024.
[2] J. Yang et al. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering. NeurIPS 2024.
[3] C. S. Xia et al. Agentless: Demystifying LLM-based Software Engineering Agents. 2024.
[4] Y. Zhang et al. AutoCodeRover: Autonomous Program Improvement. ISSTA 2024.
[5] S. Ouyang et al. RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph. ICLR 2025.
[6] X. Wang et al. OpenHands: An Open Platform for AI Software Developers as Generalist Agents. ICLR 2025.
[7] J. Pan et al. Training Software Engineering Agents and Verifiers with SWE-Gym. 2024.
[8] J. Yang et al. SWE-smith: Scaling Data for Software Engineering Agents. 2025.
[9] Google. Agent Development Kit (ADK) documentation: Agent Config. 2025-2026.
