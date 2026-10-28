"""Offline diagnostic replay; does not evaluate the model or measure treatment gain.

Animation-access detection is a lexical screen, not data-flow analysis. The 13
reported losses were also manually checked in their original transcript snippets.
Only complete echo mappings contribute to loss counts. Optional episode-prefix
arguments produce a subset and overwrite replay-results.json: preserve a full
result before using them.
"""
import os
os.environ['OPERATION_MODE'] = 'offline'
os.environ['ONLY_RESET_LEVELS'] = 'true'
# Replay creates no plots; any matplotlib import uses this ignored scratch path.
os.environ['MPLCONFIGDIR'] = str(__import__('pathlib').Path(__file__).resolve().parents[3]/'local_output/claude_review/mpl')
import json, zipfile, logging, pathlib, sys, re, time
import numpy as np
import arc_agi
from arcengine import GameAction

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT/'local_output/claude_review'
OUT.mkdir(parents=True,exist_ok=True)
logging.disable(logging.CRITICAL)
arc = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE,
    environments_dir=str(ROOT/'environment_files'), recordings_dir=str(OUT/'recordings'))
z = zipfile.ZipFile(ROOT/'downloads/results.zip')
b = json.loads(z.read('benchmark.json'))
results = []
for r in b['game_runs']:
    episode = pathlib.Path(r['solver_analysis_html']).stem
    if len(sys.argv)>1 and not any(episode.startswith(p) for p in sys.argv[1:]): continue
    text = z.read('transcripts/'+episode+'.txt').decode()
    events = [json.loads(l) for l in z.open('artifacts/'+episode+'_events.jsonl')]
    acts = [e for e in events if e['type']=='action']
    assert len(acts)==len(r['history']), episode
    env = arc.make(r['game_id'])
    before = np.array(env.observation_space.frame[-1], copy=True)
    initial = next(e for e in events if e['type']=='initial')
    if not np.array_equal(before,initial['board']):
        results.append({'episode':episode,'error':'initial mismatch'}); continue
    row = {'episode':episode,'matched':0,'total':len(acts),'score':r['final_score'],
           'levels':r['levels_completed'],'animations':[]}
    for i,(h,e) in enumerate(zip(r['history'],acts)):
        a=h['action']; assert a['id']==e['action_name']
        f=env.step(GameAction[a['id']],a.get('data',{}))
        frames=[np.asarray(x) for x in f.frame]; after=frames[-1]
        if not np.array_equal(after,e['board']):
            row['error']='board mismatch at action '+str(i+1);break
        if f.levels_completed != e['score']:
            row['error']='level mismatch at action '+str(i+1);break
        row['matched']+=1
        changes=np.zeros(before.shape,dtype=np.int16);prev=before;distinct=0
        for frame in frames:
            changed=frame!=prev
            if changed.any():distinct+=1
            changes+=changed;prev=frame
        transient=changes>=2
        endpoint_equal=np.array_equal(before[4:-4,4:-4],after[4:-4,4:-4])
        if transient.any():
            coords=np.argwhere(transient)
            row['animations'].append({'action':i+1,'display':e['action_display'],
                'analysis_step':e['analysis_step'],'level':e['level'],
                'frames':distinct,'pixels':int(transient.sum()),
                'interior_pixels':int(transient[4:-4,4:-4].sum()),
                'bbox':[int(coords[:,0].min()),int(coords[:,1].min()),int(coords[:,0].max()),int(coords[:,1].max())],
                'endpoint_unchanged':endpoint_equal,'terminal':any(e.get(k) for k in ['done','game_over','level_completed','run_complete'])})
        before=after.copy()
    # Map printed action echoes to tool calls, checking display and count.
    cursor=1 if acts and acts[0]['action_name']=='RESET' and acts[0]['analysis_step']==0 else 0
    calls=[]
    pattern=r'\[TOOL CALL: python\]\n(.*?)\n\[TOOL RESULT: python\]\n(.*?)(?=\n\[(?:ANALYZER STATUS|MODEL RESPONSE META|THINKING|TOOL CALL)|\n---|\Z)'
    mapping_ok=True
    for m in re.finditer(pattern,text,re.S):
        code,output=m.groups()
        while cursor<len(acts) and acts[cursor]['action_name']=='RESET':cursor+=1
        start=cursor
        for echo in re.findall(r'^\[action\] (.*)$',output,re.M):
            if ' -> not executed' in echo:continue
            batch=re.match(r'batch of (\d+) actions, (\d+) executed',echo)
            if batch: cursor+=int(batch[2])
            else:
                name=echo.split(' -> ')[0]
                if cursor>=len(acts) or acts[cursor]['action_display']!=name:
                    row['mapping_error']={'at':cursor+1,'expected':acts[cursor]['action_display'] if cursor<len(acts) else None,'echo':name,'line':text.count('\n',0,m.start())+1}
                    mapping_ok=False;break
                cursor+=1
        if not mapping_ok:break
        if cursor>start:
            calls.append({'start':start+1,'end':cursor,'line':text.count('\n',0,m.start())+1,
                          'reads_animation':bool(re.search(r'last_animation|\[.animation.|\.get\(.animation.',code))})
    row['mapping_ok']=mapping_ok and cursor==len(acts)
    row['mapped_actions']=cursor
    if row['mapping_ok']:
        for a in row['animations']:
            c=next((c for c in calls if c['start']<=a['action']<=c['end']),None)
            if c:a.update({'call':c, 'overwritten_before_model':a['action']<c['end'],
                          'lost_uninspected':a['action']<c['end'] and not c['reads_animation']})
    results.append(row)
    (OUT/'replay-results.json').write_text(json.dumps(results,indent=2))
    lost=[a for a in row['animations'] if a.get('lost_uninspected') and a['endpoint_unchanged'] and not a['terminal']]
    print(episode,row['matched'],'/',row['total'],'mapping',row['mapping_ok'], 'animations',len(row['animations']),'lost_noop',len(lost),row.get('error',''), flush=True)
