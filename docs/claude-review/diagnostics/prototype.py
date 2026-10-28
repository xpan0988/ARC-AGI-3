"""Isolated diagnostic; no production patch, model request or ARC action."""
import sys, pathlib, copy, json
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT))
from franzen_timeout_fixture import release_sources, load_sandbox
OUT=ROOT/'local_output/claude_review/sandbox';OUT.mkdir(parents=True,exist_ok=True)
originals,utilities=release_sources()
raw=originals['python_tool_sandbox.py'].decode()
def replace_once(s,old,new):
    assert s.count(old)==1,(old,s.count(old));return s.replace(old,new)
candidate=replace_once(raw,'        _animation_views = []','        _animation_views = []\n        _unread_transient = []\n\n        class UnreadTransientFeedback(BaseException):\n            pass')
candidate=replace_once(candidate,'            normalized_actions = _normalize_actions(actions)', '''            if _unread_transient:
                raise UnreadTransientFeedback(
                    "Next action NOT executed: the preceding action changed then reverted "
                    "during animation. Inspect last_animation_frames or last_animation_timeline; "
                    "unchanged endpoints do not establish an inert control.")
            normalized_actions = _normalize_actions(actions)''')
candidate=replace_once(candidate,'            return action_result\n\n        def _animation_fetch', '''            per_action = action_result.get("gameplay_changed_per_action")
            last_changed = per_action[-1] if isinstance(per_action, list) and per_action else gameplay_changed
            animation = action_result.get("animation") or {}
            if (action_result.get("executed") and action_result.get("level") == 1
                    and last_changed is False and animation.get("transient_pixels", 0) > 0
                    and not _terminal_state):
                _unread_transient[:] = [True]
            return action_result

        def _animation_fetch''')
candidate=replace_once(candidate,'            payload = reply.get("animation")','''            payload = reply.get("animation")
            if payload:
                _unread_transient.clear()''')
candidate=replace_once(candidate,'        except (\n            KnownNoOpActionError,','        except (\n            UnreadTransientFeedback,\n            KnownNoOpActionError,')
baseline,_=load_sandbox(OUT,raw.encode(),utilities,'control')
treatment,_=load_sandbox(OUT,candidate.encode(),utilities,'candidate')
frame={'ascii':'0','grid':[[0]],'step':0,'level':1,'shape':[1,1]}
def run(runner,code,*,changed=False,pixels=256,level=1,animation=True,empty=False,terminal=False,per_action=None):
    executed=[]
    def handle(actions,**kw):
        executed.extend(a['action'] for a in actions)
        p={'executed':True,'executed_count':len(actions),'executed_actions':[a['action'] for a in actions],
           'gameplay_changed':changed,'level':level,'action_num':len(executed),'game_over':terminal}
        if per_action is not None:p['gameplay_changed_per_action']=per_action
        if animation:p['animation']={'frames':7,'transient_pixels':pixels}
        return {'action_result':p,'state':{'current_frame':frame,'history':[], 'valid_actions':['UP','DOWN'], 'last_action_call_result':p}}
    def frames(req):
        if empty:return [] if req['kind']=='frames' else {}
        return [frame,frame] if req['kind']=='frames' else {'frames':7,'steps':[{'step':1}]}
    r=runner(code=code,timeout_seconds=3,initial_state={'current_frame':frame,'history':[],'valid_actions':['UP','DOWN']},
             action_handler=handle,animation_handler=frames,kept_functions=[])
    return executed,r
checks=[]
def check(name,ok):
    assert ok,name;checks.append(name)
code="action(['UP']); print('after first'); action(['DOWN'])"
a,r=run(baseline,code);check('baseline executes both calls',a==['UP','DOWN'] and not r.get('error'))
a,r=run(treatment,code);check('candidate stops before overwrite',a==['UP'] and 'UnreadTransientFeedback' in r.get('error','') and 'after first' in r['stdout'])
check('refusal preserves executed result and helper export',len(r['action_results'])==1 and 'keepable_functions' in r)
for name,kw in [('ordinary endpoint no-op',{'animation':False}),('animation without transient',{'pixels':0}),('persistent endpoint change',{'changed':True}),('level 2 unchanged',{'level':2})]:
    a,r=run(treatment,code,**kw);check(name,a==['UP','DOWN'] and not r.get('error'))
for accessor in ['list(last_animation_frames)','dict(last_animation_timeline)']:
    a,r=run(treatment,"action(['UP']); "+accessor+"; action(['DOWN'])");check('inspection unlocks '+accessor,a==['UP','DOWN'] and not r.get('error'))
a,r=run(treatment,"action(['UP']); list(last_animation_frames); action(['DOWN'])",empty=True)
check('empty accessor does not unlock',a==['UP'] and 'UnreadTransientFeedback' in r.get('error',''))
a,r=run(treatment,code,terminal=True);check('terminal guard retains precedence',a==['UP'] and 'TerminalStateActionError' in r.get('error',''))
a,r=run(treatment,code,changed=True,per_action=[True,False]);check('last-action flag used for batch',a==['UP'] and 'UnreadTransientFeedback' in r.get('error',''))
a,r=run(treatment,"def helper(): return 7\naction(['UP']); action(['DOWN'])")
check('helper committed on controlled handoff',any(x['name']=='helper' for x in r.get('keepable_functions',[])))
(OUT.parent/'prototype-results.json').write_text(json.dumps({'checks':checks,'passed':len(checks)},indent=2))
print(json.dumps({'passed':len(checks),'checks':checks},indent=2))
