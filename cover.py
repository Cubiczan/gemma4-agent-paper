import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np
B='localeval/'
runs=[('A r1','res_submission_r1'),('A r2','res_submission_r2'),('B r1','res_ablation_single_r1'),('B r2','res_ablation_single_r2'),('C','res_submission_fixed'),('D','res_submission_minimal')]
tasks=['rich_3882','rich_3905','rich_3894','rich_3718','rich_3935','rich_4006','rich_4075']
M=np.zeros((len(runs),len(tasks)))
for i,(n,f) in enumerate(runs):
    for l in open(B+f+'.jsonl'):
        r=json.loads(l); M[i,tasks.index(r['id'])]=r['resolved']
fig=plt.figure(figsize=(12.8,6.4),dpi=100); fig.patch.set_facecolor('#0f172a')
fig.text(0.04,0.86,'Less Scaffold, Same Fixes?',color='white',fontsize=30,weight='bold')
fig.text(0.04,0.79,'Delegation, skills and harness fidelity for budget-bound Gemma 4 coding agents',color='#cbd5e1',fontsize=15)
ax=fig.add_axes([0.08,0.12,0.5,0.55]); ax.imshow(M,cmap=matplotlib.colors.ListedColormap(['#334155','#22c55e']),aspect='auto')
ax.set_xticks(range(len(tasks)),[t.replace('rich_','#') for t in tasks],color='white',fontsize=11)
ax.set_yticks(range(len(runs)),[r[0] for r in runs],color='white',fontsize=11)
ax.set_xticks(np.arange(-.5,len(tasks)),minor=True); ax.set_yticks(np.arange(-.5,len(runs)),minor=True)
ax.grid(which='minor',color='#0f172a',linewidth=3); ax.tick_params(which='both',length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.set_title('Resolved (green) per run x task, proxy model',color='#cbd5e1',fontsize=11)
fig.text(0.63,0.55,'Localizer called: 1 / 21 runs',color='white',fontsize=17)
fig.text(0.63,0.46,'Skill loaded: 0 / 14 runs',color='white',fontsize=17)
fig.text(0.63,0.37,'With localizer 7/21  vs  without 9/21',color='white',fontsize=15)
fig.text(0.63,0.29,'(Fisher p = 0.75)',color='#94a3b8',fontsize=13)
fig.text(0.63,0.14,'Shyam (Sam) Desigan · Cubiczan',color='#94a3b8',fontsize=13)
fig.savefig('cover.png',facecolor=fig.get_facecolor())
