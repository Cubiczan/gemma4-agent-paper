"""Local proxy of the swegemma sandbox (subprocess backend style) for rich tasks."""
import json, os, re, shutil, subprocess, tempfile
HERE=os.path.dirname(os.path.abspath(__file__)); REPO=os.path.join(HERE,'rich_repo')
PY=os.path.join(HERE,'..','..','.venv','bin','python')
def sh(cmd, cwd, timeout=300, env=None):
    try:
        p=subprocess.run(['bash','-c',cmd],cwd=cwd,capture_output=True,text=True,timeout=timeout,env=env,stdin=subprocess.DEVNULL,start_new_session=True)
    except subprocess.TimeoutExpired as e:
        return 124, 'TIMEOUT after %ss'%timeout
    return p.returncode, p.stdout+p.stderr
def make_ws(task, root):
    ws=os.path.join(root,'workspace'); shutil.rmtree(root,ignore_errors=True); os.makedirs(ws)
    sh(f'git -C {REPO} archive {task["base_commit"]} | tar -x -C {ws}', HERE)
    with open(os.path.join(ws,'pytest.ini'),'w') as f: f.write('[pytest]\naddopts = -p no:cacheprovider\n')
    sh('git init -q && printf "__pycache__/\\n*.pyc\\n.pytest_cache/\\n*.egg-info/\\nbuild/\\ndist/\\n" >> .git/info/exclude && git add -A && git -c user.email=a@b -c user.name=b commit -qm baseline', ws)
    return ws
def penv(ws):
    e=dict(os.environ); e['PATH']=os.path.dirname(PY)+':'+e['PATH']; e['PYTHONPATH']=ws
    for k in list(e):
        if 'KEY' in k or 'TOKEN' in k or 'SECRET' in k: e.pop(k)
    return e
def verify(task, patch, root):
    ws=make_ws(task, root)
    if patch.strip():
        open(os.path.join(root,'a.patch'),'w').write(patch)
        rc,o=sh(f'git apply ../a.patch || git apply -3 ../a.patch || patch -p1 --batch --forward < ../a.patch', ws)
        if rc: return False, 'apply failed: '+o[-500:]
    tfiles=re.findall(r'^\+\+\+ b/(\S+)', task['test_patch'], re.M)
    sh('git checkout HEAD -- '+' '.join(tfiles)+' 2>/dev/null; git clean -fq -- '+' '.join(tfiles), ws)
    open(os.path.join(root,'t.patch'),'w').write(task['test_patch'])
    rc,o=sh('git apply ../t.patch', ws)
    if rc: return False,'test patch failed '+o
    rc,o=sh(f'PYTHONSAFEPATH=1 python -m pytest {" ".join(tfiles)} -p no:anyio -q -x 2>&1 | tail -15; exit ${{PIPESTATUS[0]}}', ws, env=penv(ws), timeout=120)
    return rc==0, o[-1500:]
if __name__=='__main__':
    for l in open(os.path.join(HERE,'tasks.jsonl')):
        t=json.loads(l); r=tempfile.mkdtemp()
        g,_=verify(t,t['patch'],r); b,o=verify(t,'',r)
        print(t['instance_id'],'gold_pass=',g,'empty_pass=',b)
