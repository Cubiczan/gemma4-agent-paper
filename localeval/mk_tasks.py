import json, subprocess, re, urllib.request
R='rich_repo'
PRS={4075:'9cb198944f8184df92217efc8b20d3fffa4b4fa0',3937:'05ff970926cbd0b5d0acb6fc18cdbd1fc971e582',3882:'abd5a2afc41ff1196fe4d901b8784bb08acf3140',
 3894:'12eeb42c96a7a953865b19da204dea6fe658713b',3905:'fe55a131c2780fa856464ad04d7d6dc8a1079b72',3718:'21b3800894f6a81d3f68a0e34796be67e3ccd39f',
 3935:'9e18b96652f37293121b04017fb6aa95af21b013',4006:'7338cb9dafd0d0e916585f191ae505b3e602bb51'}
def gh(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'x'})))
    except Exception as e: return {}
g=lambda *a: subprocess.run(['git','-C',R,*a],capture_output=True,text=True).stdout
out=open('tasks.jsonl','w')
for n,h in PRS.items():
    base=g('rev-parse',h+'^1').strip()
    files=g('diff','--name-only',base,h).split()
    src=[f for f in files if f.startswith('rich/')]; tst=[f for f in files if f.startswith('tests/')]
    pr=gh(f'https://api.github.com/repos/Textualize/rich/pulls/{n}')
    body=(pr.get('body') or ''); title=pr.get('title','')
    m=re.search(r'(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?|fix for)\s+(?:#|https://github.com/Textualize/rich/issues/)(\d+)',body,re.I)
    ps=f'{title}\n\n{body}'
    if m:
        iss=gh(f'https://api.github.com/repos/Textualize/rich/issues/{m.group(1)}')
        if iss: ps=f"{iss.get('title','')}\n\n{iss.get('body') or ''}"
    # strip PR checklist boilerplate
    ps=re.sub(r'## Type of changes.*?(?=\n## |\Z)','',ps,flags=re.S); ps=re.sub(r'## Checklist.*?(?=\n## |\Z)','',ps,flags=re.S)
    out.write(json.dumps(dict(instance_id=f'rich_{n}',repo='Textualize/rich',base_commit=base,problem_statement=ps.strip()[:6000],
        hints_text='',patch=g('diff',base,h,'--',*src),test_patch=g('diff',base,h,'--',*tst)))+'\n')
    print(n, len(ps), src, tst, bool(m))
