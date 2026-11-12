"""Validate submission/ with the organizers' adk_submission 0.2.11 compiler + swegemma limits,
using stub tools with the harness signatures. Then build submission.zip."""
import sys, os, zipfile, pathlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'official_harness_ref'))
import importlib.util
from adk_submission import compile_submission, ModelRegistry
# load swegemma/config.py constants without importing the heavy swegemma package
spec = importlib.util.spec_from_file_location('sgcfg', os.path.join(os.path.dirname(__file__), '..', 'official_harness_ref', 'swegemma', 'config.py'))
from google.adk.models.lite_llm import LiteLlm

def run_command(command: str) -> str: return ''
def submit_patch() -> str: return ''
def get_status() -> str: return ''
def read_file(filepath: str, start_line: int | None = None, end_line: int | None = None) -> str: return ''
def edit_file(filepath: str, old_string: str, new_string: str, allow_multiple: bool = False) -> str: return ''
def write_file(filepath: str, content: str) -> str: return ''
def get_code_neighbors(node: str, edge_type: str | None = None, max_neighbors: int = 50) -> str: return ''
def search_similar_code(query: str, k: int = 10) -> str: return ''
def get_code_subgraph(nodes: list[str]) -> str: return ''
TOOLS = {f.__name__: f for f in [run_command, submit_patch, get_status, read_file, edit_file, write_file,
                                 get_code_neighbors, search_similar_code, get_code_subgraph]}
ALIASES = ['gemma-4-31b-it-qat-w4a16-ct','gemma-4-12b-it-qat-w4a16-ct','gemma-4-e4b-it-qat-w4a16-ct','gemma-4-e2b-it-qat-w4a16-ct']

def limits():
    try:
        from swegemma.config import build_submission_limits
        return build_submission_limits()
    except Exception as e:
        print('WARN: could not load swegemma limits (', e, '); using adk_submission defaults')
        return None, None

def main(sub='submission', out='submission.zip'):
    reg = ModelRegistry()
    for a in ALIASES:
        reg.register(a, LiteLlm(model=f'openai/{a}', api_base='http://127.0.0.1:8000/v1', api_key='EMPTY'))
    lim, gen = limits()
    kw = dict(limits=lim, generation_constraints=gen) if lim else {}
    agent = compile_submission(sub, TOOLS, reg, **kw)
    def walk(a, d=0):
        tools = [getattr(t, 'name', type(t).__name__) for t in getattr(a, 'tools', [])]
        print('  '*d + f'{a.name} [{type(a).__name__}] model={getattr(getattr(a,"model",None),"model",getattr(a,"model",None))} tools={tools}')
        for s in getattr(a, 'sub_agents', []): walk(s, d+1)
        for t in getattr(a, 'tools', []):
            if hasattr(t, 'agent'): walk(t.agent, d+1)
    walk(agent)
    # single-model rule
    import yaml, re
    models = set()
    for p in pathlib.Path(sub).rglob('*.y*ml'):
        models |= set(re.findall(r'^model:\s*(\S+)', p.read_text(), re.M))
    assert len(models) == 1, models; print('single model OK:', models)
    bad = [p for p in pathlib.Path(sub).rglob('*') if p.is_file() and p.suffix not in {'.yaml','.yml','.md','.txt','.py','.json','.safetensors'}]
    assert not bad, bad
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(pathlib.Path(sub).rglob('*')):
            if p.is_file(): z.write(p, p.relative_to(sub).as_posix())
    names = zipfile.ZipFile(out).namelist(); assert 'agent.yaml' in names
    print('wrote', out, len(names), 'files', os.path.getsize(out), 'bytes'); print('\n'.join(names))

if __name__ == '__main__':
    main(*sys.argv[1:])
