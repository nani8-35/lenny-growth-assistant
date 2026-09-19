"""Idempotent, atomic per-episode indexing. Run from backend: python -m scripts.ingest."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import yaml
from app import db
from app.config import settings
from app.retrieval import embed

TIMESTAMP=re.compile(r'\b(?:\d{1,2}:)?\d{1,2}:\d{2}\b')
def parse_transcript(text, fallback='Unknown guest'):
    metadata={}
    if text.startswith('---'):
        pieces=text.split('---',2)
        if len(pieces)==3:
            metadata=yaml.safe_load(pieces[1]) or {};text=pieces[2]
    return {'title':str(metadata.get('title',fallback)), 'guest':str(metadata.get('guest',fallback)),
            'published':str(metadata.get('publish_date','')), 'source_url':str(metadata.get('youtube_url',''))},text.strip()

def chunk_text(text, target=2400, overlap=400):
    """Recursive boundary preference; ~600 tokens and ~100 overlap at 4 chars/token."""
    chunks=[];start=0;last_timestamp=None
    while start<len(text):
        end=min(start+target,len(text))
        if end<len(text):
            for separator in ('\n\n','\n','. ',' '):
                boundary=text.rfind(separator,start+target//2,end)
                if boundary!=-1:
                    end=boundary+len(separator);break
        body=text[start:end].strip()
        found=TIMESTAMP.findall(body)
        timestamp=found[0] if found else last_timestamp
        if body:chunks.append({'content':body,'timestamp_ref':timestamp})
        if found:last_timestamp=found[-1]
        if end==len(text):break
        start=max(start+1,end-overlap)
    return chunks

async def run(args):
    p=await db.pool();await db.initialize(p)
    root=Path(args.path);files=sorted(root.glob('*/transcript.md'))
    if args.guests:files=[f for f in files if any(g.lower() in f.parent.name.lower() for g in args.guests.split(','))]
    if args.limit:files=files[:args.limit]
    if not files:raise SystemExit('No transcripts found. Run download_transcripts first.')
    indexed=skipped=0
    try:
        for file in files:
            raw=file.read_text();key=file.parent.name;checksum=hashlib.sha256(raw.encode()).hexdigest()
            old=await p.fetchrow('SELECT checksum,embedding_model FROM episodes WHERE id=$1',key)
            if old and old['checksum']==checksum and old['embedding_model']==settings().embedding_model and not args.force:
                skipped+=1;continue
            metadata,body=parse_transcript(raw,key)
            if not metadata['source_url']:metadata['source_url']=f'https://github.com/ChatPRD/lennys-podcast-transcripts/blob/main/episodes/{key}/transcript.md'
            chunks=chunk_text(body);vectors=[]
            for i in range(0,len(chunks),8):
                vectors.extend(await embed(['search_document: '+c['content'] for c in chunks[i:i+8]]))
            async with p.acquire() as conn:
                async with conn.transaction():
                    await conn.execute('''INSERT INTO episodes(id,title,guest,published,source_url,checksum,embedding_model)
                    VALUES($1,$2,$3,$4,$5,$6,$7) ON CONFLICT(id) DO UPDATE SET title=$2,guest=$3,published=$4,source_url=$5,checksum=$6,embedding_model=$7,indexed_at=now()''',key,metadata['title'],metadata['guest'],metadata['published'],metadata['source_url'],checksum,settings().embedding_model)
                    await conn.execute('DELETE FROM chunks WHERE episode_id=$1',key)
                    await conn.executemany('INSERT INTO chunks(episode_id,ordinal,content,timestamp_ref,embedding) VALUES($1,$2,$3,$4,$5::vector)',[(key,i,c['content'],c['timestamp_ref'],str(v)) for i,(c,v) in enumerate(zip(chunks,vectors))])
            indexed+=1
            print(json.dumps({'event':'episode_indexed','episode':key,'chunks':len(chunks)}),flush=True)
        print(json.dumps({'event':'ingestion_complete','indexed':indexed,'skipped':skipped}))
    finally:await p.close()
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--path',default='../data/transcripts');parser.add_argument('--limit',type=int);parser.add_argument('--guests');parser.add_argument('--force',action='store_true');asyncio.run(run(parser.parse_args()))
