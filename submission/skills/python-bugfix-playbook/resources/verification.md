# Fast verification

1. Scratch files go in /tmp only. Anything new under /workspace ends up in the patch.
2. Repro: `cd /workspace && python /tmp/repro.py` with plain asserts.
3. Targeted tests: `cd /workspace && python -m pytest tests/<closest_file>.py -x -q 2>&1 | tail -20`.
4. Diff hygiene: `git status --short` must list only library files you meant to change; never pytest.ini or conftest.py.
5. Then call submit_patch.
