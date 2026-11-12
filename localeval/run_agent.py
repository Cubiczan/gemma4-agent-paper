"""Run the compiled submission (official adk_submission compiler) on local tasks with a proxy
model over an OpenAI-compatible endpoint. Mirrors swegemma tool limits & prompt; graph tools are
approximated with an AST index (the competition's precomputed graphs/embeddings are not available
without Kaggle data access)."""
import ast, asyncio, json, os, re, sys, tempfile, time
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(HERE,'..','..','official_harness_ref'))
from env import make_ws, verify, sh, penv
from adk_submission import compile_submission, ModelRegistry
from swegemma.config import build_submission_limits
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
PROXY=os.environ.get('PROXY_MODEL','gpt-4.1-mini'); BASE=os.environ.get('PROXY_BASE','https://api.openai.com/v1'); KEYVAR=os.environ.get('PROXY_KEYVAR','OPENAI_API_KEY')
MAX_MIN=float(os.environ.get('MAX_MIN','8')); MAX_CALLS=int(os.environ.get('MAX_CALLS','40'))

class Ctx:
    def __init__(s, ws): s.ws=ws; s.calls=0; s.t0=time.time(); s.submitted=False; s.idx=None
    def gate(s):
        s.calls+=1
        if s.calls>MAX_CALLS or time.time()-s.t0>MAX_MIN*60: return json.dumps({'error':'budget exhausted; call submit_patch now'})
    def p(s, fp):
        fp=fp.replace('/workspace',s.ws,1) if fp.startswith('/workspace') else os.path.join(s.ws,fp)
        return fp
    def index(s):
        if s.idx is None:
            s.idx={}
            for dp,_,fs in os.walk(os.path.join(s.ws,'rich')):
                for f in fs:
                    if not f.endswith('.py'): continue
                    fp=os.path.join(dp,f); src=open(fp).read(); mod='rich.'+os.path.relpath(fp,os.path.join(s.ws,'rich'))[:-3].replace('/','.')
                    try: tree=ast.parse(src)
                    except Exception: continue
                    def visit(n, pref):
                        for c in ast.iter_child_nodes(n):
                            if isinstance(c,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                                q=pref+'.'+c.name; s.idx[q]=(os.path.relpath(fp,s.ws),c.lineno,ast.get_source_segment(src,c) or ''); visit(c,q)
                    visit(tree, mod)
        return s.idx

def make_tools(c):
    def run_command(command: str) -> str:
        """Execute a shell command with /bin/bash -c inside /workspace."""
        if (e:=c.gate()): return e
        try: rc,o=sh(command.replace('/workspace',c.ws), c.ws, timeout=120, env=penv(c.ws))
        except Exception as ex: return json.dumps({'error':'timeout'})
        return json.dumps({'exit_code':rc,'output':o[-5000:]})
    def submit_patch() -> str:
        """Stage new files and capture git diff HEAD from /workspace as the final patch."""
        sh('git add -N .', c.ws); _,d=sh('git diff HEAD', c.ws); c.submitted=True; c.patch=d
        return json.dumps({'status':'submitted','patch_chars':len(d)})
    def get_status() -> str:
        """Return budget consumption."""
        return json.dumps({'elapsed_s':round(time.time()-c.t0),'max_time_minutes':MAX_MIN,'tool_calls':c.calls,'max_tool_calls':MAX_CALLS})
    def read_file(filepath: str, start_line: int | None = None, end_line: int | None = None) -> str:
        """Read a file from /workspace with 1-indexed inclusive line slicing (max 150 lines)."""
        if (e:=c.gate()): return e
        try: L=open(c.p(filepath)).read().splitlines()
        except Exception as ex: return json.dumps({'error':str(ex)})
        a=max(1,start_line or 1); b=min(len(L), end_line or a+149, a+149)
        return '\n'.join(f'{i}: {L[i-1]}' for i in range(a,b+1))[:10000]+f'\n[lines {a}-{b} of {len(L)}]'
    def edit_file(filepath: str, old_string: str, new_string: str, allow_multiple: bool = False) -> str:
        """Replace old_string with new_string in an existing file in /workspace."""
        if (e:=c.gate()): return e
        fp=c.p(filepath)
        try: s=open(fp).read()
        except Exception as ex: return json.dumps({'error':str(ex)})
        n=s.count(old_string)
        if n==0: return json.dumps({'error':'old_string not found'})
        if n>1 and not allow_multiple: return json.dumps({'error':f'old_string found {n} times; make it unique'})
        open(fp,'w').write(s.replace(old_string,new_string)); return json.dumps({'status':'ok','replacements':n})
    def write_file(filepath: str, content: str) -> str:
        """Create or overwrite a file under /workspace."""
        if (e:=c.gate()): return e
        fp=c.p(filepath); os.makedirs(os.path.dirname(fp),exist_ok=True); open(fp,'w').write(content); return json.dumps({'status':'ok'})
    def search_similar_code(query: str, k: int = 10) -> str:
        """Find top-k code symbols most similar to the query."""
        if (e:=c.gate()): return e
        toks=set(re.findall(r'[a-z0-9]+',query.lower()))
        sc=[]
        for q,(f,ln,src) in c.index().items():
            w=re.findall(r'[a-z0-9]+',(q+' '+src[:1500]).lower()); ws=set(w)
            sc.append((len(toks&ws)+2*len(toks&set(re.findall(r'[a-z0-9]+',q.lower()))),q,f,ln))
        sc.sort(reverse=True); return json.dumps([{'node':q,'file':f,'line':ln} for _,q,f,ln in sc[:k]])
    def get_code_neighbors(node: str, edge_type: str | None = None, max_neighbors: int = 50) -> str:
        """Find callers and callees of a symbol in the code graph."""
        if (e:=c.gate()): return e
        idx=c.index(); m=[q for q in idx if q==node or q.endswith('.'+node)]
        if not m: return json.dumps({'error':'node not found'})
        q=m[0]; name=q.split('.')[-1]; src=idx[q][2]
        out=[{'node':o,'dir':'outgoing','type':'calls'} for o in idx if o!=q and re.search(r'\b'+re.escape(o.split('.')[-1])+r'\(',src)]
        inc=[{'node':o,'dir':'incoming','type':'calls'} for o,(f,l,s) in idx.items() if o!=q and re.search(r'\b'+re.escape(name)+r'\(',s)]
        return json.dumps({'node':q,'file':idx[q][0],'line':idx[q][1],'neighbors':(out+inc)[:max_neighbors]})
    def get_code_subgraph(nodes: list[str]) -> str:
        """Extract the induced subgraph for a list of symbols."""
        if (e:=c.gate()): return e
        idx=c.index(); ns=[q for q in idx if any(q==n or q.endswith('.'+n) for n in nodes)]
        ed=[(a,b) for a in ns for b in ns if a!=b and re.search(r'\b'+re.escape(b.split('.')[-1])+r'\(',idx[a][2])]
        return json.dumps({'nodes':[{'id':q,'file':idx[q][0],'line':idx[q][1]} for q in ns],'edges':[{'source':a,'target':b,'type':'calls'} for a,b in ed]})
    return {f.__name__:f for f in [run_command,submit_patch,get_status,read_file,edit_file,write_file,search_similar_code,get_code_neighbors,get_code_subgraph]}

def prompt(t, ws):
    _,tree=sh('find . -maxdepth 3 -not -path "./.git/*" -not -name "*.pyc" -not -name "__pycache__" | sort | head -150', ws)
    return f"""You are evaluating a software engineering task for repository {t['repo']}.

Problem Statement:
{t['problem_statement']}

## Task Budget (Session terminates when any budget is exhausted)
- Time allowance: {MAX_MIN} minutes
- Tool calls allowance: {MAX_CALLS} calls

## Execution Environment Rules
- Single command timeout: 120 seconds
- Command output limit: 5000 characters
- File view limit: 150 lines per read_file call
- Environment is offline (no network/PyPI access). All repository and test dependencies are ALREADY pre-installed. Do NOT attempt to run pip install or download packages.

## Instructions
0. Work strictly under /workspace. 1. Inspect existing conventions. 2. Make the change. 3. Verify with targeted checks. 4. Call submit_patch once complete. 5. Then give a short final text response.

## Code Intelligence Tools
This repository has pre-built code graph and embedding data. Use these tools for fast, targeted navigation:
- `search_similar_code(query)`: Find semantically similar functions/classes by keyword.
- `get_code_neighbors(node)`: Find callers, callees, and definitions related to a symbol.
- `get_code_subgraph(nodes)`: Get the induced subgraph for a set of symbols.

## Workspace Layout
{tree}"""

async def run_task(t, sub):
    root=tempfile.mkdtemp(prefix='ag_'); ws=make_ws(t, root+'/a'); c=Ctx(ws); c.patch=''
    reg=ModelRegistry()
    for a in ['gemma-4-31b-it-qat-w4a16-ct','gemma-4-e4b-it-qat-w4a16-ct']:
        reg.register(a, LiteLlm(model='openai/'+PROXY, api_base=BASE, api_key=os.environ[KEYVAR], num_retries=3))
    lim,gen=build_submission_limits()
    agent=compile_submission(sub, make_tools(c), reg, limits=lim, generation_constraints=gen)
    def strip(a):  # proxy-only: OpenAI rejects vLLM's chat_template_kwargs produced from thinking_config
        g=getattr(a,'generate_content_config',None)
        if g is not None and getattr(g,'thinking_config',None) is not None: g.thinking_config=None
        m=getattr(a,'model',None)
        if hasattr(m,'_additional_args') and isinstance(m._additional_args,dict):
            m._additional_args.pop('extra_body',None); m._additional_args.pop('reasoning_effort',None)
        for x in getattr(a,'sub_agents',[]): strip(x)
        for t in getattr(a,'tools',[]):
            if hasattr(t,'agent'): strip(t.agent)
    if os.environ.get('STRIP_THINKING','1')=='1': strip(agent)
    ss=InMemorySessionService(); r=Runner(agent=agent, app_name='swegemma_eval', session_service=ss)
    s=await ss.create_session(app_name='swegemma_eval', user_id='u', state={'problem_description':t['problem_statement']})
    msg=prompt(t, ws); nudges=0; trace=[]; err=None
    while True:
        had_tool=False
        try:
            async for ev in r.run_async(user_id='u', session_id=s.id, new_message=types.Content(role='user',parts=[types.Part(text=msg)])):
                for p in (ev.content.parts if ev.content else []) or []:
                    if p.function_call: had_tool=True; trace.append(('call',ev.author,p.function_call.name,str(p.function_call.args)[:300]))
                    elif p.text: trace.append(('text',ev.author,p.text[:300]))
                if c.submitted: break
        except Exception as ex:
            err=str(ex)[:300]; trace.append(('error','',err)); had_tool=False
        if err and len([x for x in trace if x[0]=='error'])>3: break
        if c.submitted or time.time()-c.t0>MAX_MIN*60 or c.calls>MAX_CALLS: break
        nudges = 0 if had_tool else nudges+1
        if nudges>3: break
        msg='Please continue your work using the available tools, or call submit_patch when you have completed and verified your changes.'
    if not c.submitted: sh('git add -N .', ws); _,c.patch=sh('git diff HEAD', ws)
    elapsed=time.time()-c.t0
    ok,log=verify(t, c.patch, root+'/b') if c.patch.strip() else (False,'empty patch')
    return dict(id=t['instance_id'],resolved=ok,submitted=c.submitted,tool_calls=c.calls,elapsed_s=round(elapsed),
                patch_lines=len(c.patch.splitlines()),localizer_used=any(x[0]=='call' and x[2]=='localizer' for x in trace),
                skill_used=any(x[0]=='call' and 'skill' in x[2] for x in trace),error=err,verify_tail=log[-400:],patch=c.patch,trace=trace)

async def main():
    sub=sys.argv[1]; out=sys.argv[2]; ids=sys.argv[3:]
    tasks=[json.loads(l) for l in open(os.path.join(HERE,'tasks.jsonl'))]
    tasks=[t for t in tasks if not ids or t['instance_id'] in ids]
    with open(out,'a') as f:
        for t in tasks:
            res=await run_task(t, sub); f.write(json.dumps(res)+'\n'); f.flush()
            print(res['id'],'resolved=',res['resolved'],'calls=',res['tool_calls'],'t=',res['elapsed_s'],'loc=',res['localizer_used'],'err=',res['error'],flush=True)
asyncio.run(main())
