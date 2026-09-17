import os,json,subprocess,hashlib,pathlib
from runtime_registry import load_context
PREFERRED=['/generate','/chat','/predict','/respond','/infer','/run']
ROLE=os.environ['ROLE']; MODEL=os.environ['MODEL']; FOCUS=os.environ.get('FOCUS','formal audit')
MISSION=pathlib.Path('MISSION.md').read_text(encoding='utf-8')
REGISTRY_CONTEXT,REGISTRY_META=load_context(['constitution','disciplines','keys'])

def run(cmd,timeout=240):
    try: return subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    except Exception as e:
        class R: returncode=1; stdout=''; stderr=repr(e)
        return R()

def payload(spec,prompt):
    d={}
    for p in spec.get('parameters',[]):
        n=p.get('parameter_name') or p.get('name',''); req=p.get('parameter_has_default') is False
        if n in ('message','prompt','text','query','input','instruction','user_message'): d[n]=prompt
        elif 'history' in n: d[n]=[]
        elif n in ('max_new_tokens','max_tokens'): d[n]=700
        elif n=='temperature': d[n]=0.1
        elif n=='top_p': d[n]=0.9
        elif n=='top_k': d[n]=40
        elif n in ('system','system_prompt'): d[n]='Formal verification auditor. CLAIM<=EVIDENCE. PROOF!=HEURISTIC.'
        elif req: d[n]=prompt
    return d

def extract(s):
    try:
        x=json.loads(s)
        if isinstance(x,dict):
            for k in ('Response','response','text','output','message'):
                if k in x and x[k] is not None: return str(x[k]).strip()
    except: pass
    return s.strip()

def invoke(space,prompt):
    info=run(['hf-gradio','info',space],120)
    if info.returncode!=0: return False,'',{'error':info.stderr[-1200:]}
    try: data=json.loads(info.stdout)
    except Exception as e: return False,'',{'error':'info_json:'+repr(e)}
    eps=data.get('named_endpoints') or data.get('endpoints') or {}
    items=[]
    if isinstance(eps,dict): items=list(eps.items())
    elif isinstance(eps,list): items=[(x.get('api_name',''),x) for x in eps]
    items.sort(key=lambda kv:(PREFERRED.index(kv[0]) if kv[0] in PREFERRED else 999))
    errs=[]
    for ep,spec in items:
        if not ep: continue
        pred=run(['hf-gradio','predict',space,ep,json.dumps(payload(spec,prompt))],240)
        if pred.returncode==0:
            text=extract(pred.stdout)
            if text: return True,text,{'endpoint':ep,'sha256':hashlib.sha256(text.encode()).hexdigest()}
        errs.append((ep,pred.stderr[-700:]))
    return False,'',{'error':repr(errs[-4:])}

prompt=f'''You are {ROLE} in CEREBRON Omega Farm 34 Formal Audit. Focus: {FOCUS}.\n{MISSION}\nCEREBRON RUNTIME CONTEXT (shared registry; guidance only, never self-certifying):\n{REGISTRY_CONTEXT}\nAudit the target reasoning class rigorously. Return: CLAIMS, PREMISES, FORMAL DEPENDENCIES, VALID STEPS, INVALID/UNPROVED STEPS, EDGE CASES, COUNTERMODELS OR COUNTEREXAMPLES, DIMENSION/TYPE/DOMAIN CHECKS, REPRODUCTION REQUIREMENTS, EVIDENCE GAPS, VERDICT PER CLAIM, NEXT DECISIVE CHECK. Never upgrade an unproved claim.'''
ok,text,meta=invoke(MODEL,prompt)
rec={'farm':34,'role':ROLE,'model':MODEL,'focus':FOCUS,'inference_success':ok,'status':'UNREVIEWED_EXTERNAL_AGENT_OUTPUT' if ok else 'EXTERNAL_INFERENCE_FAILED','output':text if ok else None,'registry_runtime':REGISTRY_META,'meta':meta}
pathlib.Path('results').mkdir(exist_ok=True)
pathlib.Path(f'results/{ROLE}.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'role':ROLE,'inference_success':ok,'status':rec['status'],'registry_runtime':REGISTRY_META}))
