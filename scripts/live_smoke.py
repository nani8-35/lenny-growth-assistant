"""Exercise the actual API and model. Saves evidence without secrets."""
import argparse,json,time
from pathlib import Path
import httpx
parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8000');parser.add_argument('--mode',default='answer');parser.add_argument('--provider',choices=('ollama','anthropic'),default='ollama');parser.add_argument('--question',default='How does Rahul Vohra measure product-market fit?');parser.add_argument('--output',default='docs/live-smoke.json');args=parser.parse_args()
with httpx.Client(base_url=args.url,timeout=300) as client:
    s=client.post('/api/sessions',json={'title':'Verification: '+args.mode});s.raise_for_status();sid=s.json()['id']
    start=time.monotonic();events=[];first=None
    with client.stream('POST','/api/chat',json={'session_id':sid,'message':args.question,'provider':args.provider,'mode':args.mode}) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith('data: '):
                event=json.loads(line[6:]);events.append(event)
                if event['type']=='token' and first is None:first=round(time.monotonic()-start,3)
    history=client.get('/api/sessions/'+sid).json()
    result={'question':args.question,'mode':args.mode,'provider':args.provider,'session_id':sid,'first_token_seconds':first,'total_seconds':round(time.monotonic()-start,3),'terminal':events[-1] if events else None,'warnings':[e for e in events if e['type']=='warning'],'history':history}
    Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='history'},indent=2))
    print(history.get('messages',[{}])[-1].get('content','')[:2500])
