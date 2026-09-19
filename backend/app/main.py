import asyncio
import json
import logging
import re
import time
from contextlib import asynccontextmanager
from uuid import UUID, uuid4
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal
from .config import settings
from . import db
from .retrieval import retrieve, contextual_query, validate_citations, ABSTENTION

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger('lenny')

def event_log(event, **fields):
    log.info(json.dumps({'event': event, **fields}, default=str))

@asynccontextmanager
async def lifespan(app):
    app.state.pool = None
    try:
        app.state.pool = await db.pool()
        await db.initialize(app.state.pool)
    except Exception as exc:
        event_log('database_startup_failed', error=type(exc).__name__)
    yield
    if app.state.pool:
        await app.state.pool.close()

app = FastAPI(title='Lenny Growth Assistant', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings().cors_origin], allow_methods=['GET','POST'], allow_headers=['Content-Type','X-Workspace-Token'])

@app.middleware('http')
async def request_id(request, call_next):
    request.state.request_id = str(uuid4())
    start = time.monotonic()
    response = await call_next(request)
    response.headers['X-Request-ID'] = request.state.request_id
    event_log('http_request', request_id=request.state.request_id, path=request.url.path,
              status=response.status_code, duration_ms=round((time.monotonic()-start)*1000))
    return response

@app.exception_handler(Exception)
async def unexpected(request, exc):
    event_log('unhandled_error', request_id=getattr(request.state,'request_id',None), error=type(exc).__name__)
    return JSONResponse(status_code=503, content={'error': {'code':'service_unavailable','message':'A service is unavailable. Check system status and retry.','request_id':getattr(request.state,'request_id',None)}})

@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(status_code=exc.status_code, content={'error': {'code':str(exc.status_code),'message':exc.detail,'request_id':getattr(request.state,'request_id',None)}})

async def get_pool():
    if app.state.pool is None:
        try:
            app.state.pool = await db.pool()
            await db.initialize(app.state.pool)
        except Exception:
            raise HTTPException(503, 'PostgreSQL is unavailable. Start the database and retry.')
    return app.state.pool

def serialize(row):
    d = dict(row)
    for k,v in d.items():
        if isinstance(v, UUID): d[k] = str(v)
        elif hasattr(v,'isoformat'): d[k] = v.isoformat()
        elif k in ('sources','user_metadata') and isinstance(v,str): d[k]=json.loads(v)
    return d

class NewSession(BaseModel):
    title: str = Field(default='New conversation', min_length=1, max_length=120)
    user_metadata: dict[str,str] = Field(default_factory=dict, max_length=10)

class Chat(BaseModel):
    session_id: UUID
    message: str = Field(min_length=1, max_length=8000)
    provider: Literal['ollama','anthropic','gemini'] | None = None
    mode: Literal['answer','essay','markdown','html'] = 'answer'

def owner_token(request: Request):
    token=request.headers.get('X-Workspace-Token','')
    if len(token)<24 or len(token)>128: raise HTTPException(401,'A valid workspace token is required.')
    return token

@app.post('/api/sessions', status_code=201)
async def create_session(body: NewSession, request: Request):
    p=await get_pool(); token=owner_token(request)
    row=await p.fetchrow('INSERT INTO sessions(id,title,user_metadata,owner_token) VALUES($1,$2,$3,$4) RETURNING *',uuid4(),body.title,json.dumps(body.user_metadata),token)
    return serialize(row)

@app.get('/api/sessions')
async def sessions(request: Request):
    p=await get_pool(); token=owner_token(request)
    return [serialize(r) for r in await p.fetch('SELECT * FROM sessions WHERE owner_token=$1 ORDER BY updated_at DESC LIMIT 100',token)]

@app.get('/api/sessions/{session_id}')
async def session(session_id: UUID, request: Request):
    p=await get_pool(); token=owner_token(request)
    row=await p.fetchrow('SELECT * FROM sessions WHERE id=$1 AND owner_token=$2',session_id,token)
    if not row: raise HTTPException(404,'Conversation not found')
    messages=[serialize(r) for r in await p.fetch('SELECT * FROM messages WHERE session_id=$1 ORDER BY created_at,id',session_id)]
    arts=[serialize(r) for r in await p.fetch('SELECT a.* FROM artifacts a JOIN messages m ON a.message_id=m.id WHERE m.session_id=$1 ORDER BY a.created_at',session_id)]
    return {**serialize(row),'messages':messages,'artifacts':arts}

@app.get('/api/artifacts/{artifact_id}')
async def artifact(artifact_id: UUID, request: Request):
    p=await get_pool(); token=owner_token(request)
    row=await p.fetchrow('SELECT a.* FROM artifacts a JOIN messages m ON m.id=a.message_id JOIN sessions s ON s.id=m.session_id WHERE a.id=$1 AND s.owner_token=$2',artifact_id,token)
    if not row: raise HTTPException(404,'Artifact not found')
    return serialize(row)

@app.get('/api/health')
async def health():
    result={'database':False,'chunks':0,'episodes':0,'ollama':False,'agent':False,'cloud_configured':False,'gemini_configured':False,'default_provider':settings().default_llm_provider}
    try:
        p=await get_pool()
        result.update(database=True,chunks=await p.fetchval('SELECT count(*) FROM chunks'),episodes=await p.fetchval('SELECT count(*) FROM episodes'))
    except Exception: pass
    async with httpx.AsyncClient(timeout=3) as client:
        async def check_ollama():
            try:
                r=await client.get(settings().ollama_base_url+'/api/tags'); r.raise_for_status()
                result['ollama']=True; result['models']=[m['name'] for m in r.json()['models']]
            except Exception: pass
        async def check_agent():
            try:
                r=await client.get(settings().agent_url+'/health'); r.raise_for_status()
                result.update(agent=True,**r.json())
            except Exception: pass
        await asyncio.gather(check_ollama(),check_agent())
    names=result.get('models',[])
    provider=settings().default_llm_provider
    if provider=='gemini':
        result['generation_model_ready']=result['gemini_configured']
    elif provider=='anthropic':
        result['generation_model_ready']=result['cloud_configured']
    else:
        result['generation_model_ready']=any(n==result.get('ollama_model') or n==str(result.get('ollama_model'))+':latest' for n in names)
    result['embedding_model_ready']=settings().retrieval_mode=='lexical' or any(n==settings().embedding_model or n==settings().embedding_model+':latest' for n in names)
    result['ready']=result['database'] and result['chunks']>0 and result['agent'] and result['generation_model_ready'] and result['embedding_model_ready']
    return result

def sse(kind, **data):
    return 'data: '+json.dumps({'type':kind,**data},default=str)+'\n\n'

@app.post('/api/chat')
async def chat(body: Chat, request: Request):
    token=owner_token(request)
    if not body.message.strip(): raise HTTPException(422,'Enter a question')
    provider=body.provider or settings().default_llm_provider
    p=await get_pool()
    conn=await p.acquire()
    lock=False
    try:
        lock=await conn.fetchval('SELECT pg_try_advisory_lock(hashtextextended($1,0))',str(body.session_id))
        if not lock: raise HTTPException(409,'This conversation is already generating a response')
        if not await conn.fetchval('SELECT 1 FROM sessions WHERE id=$1 AND owner_token=$2',body.session_id,token):
            raise HTTPException(404,'Conversation not found')
        async with httpx.AsyncClient(timeout=5) as client:
            status=await client.get(settings().agent_url+'/health'); status.raise_for_status()
            if provider=='anthropic' and not status.json().get('cloud_configured'):
                raise HTTPException(503,'Add ANTHROPIC_API_KEY to .env and restart the agent. No automatic fallback is used.')
            if provider=='gemini' and not status.json().get('gemini_configured'):
                raise HTTPException(503,'Add GEMINI_API_KEY to .env and restart the agent. No automatic fallback is used.')
        history=[serialize(r) for r in await conn.fetch('SELECT role,content FROM (SELECT role,content,created_at FROM messages WHERE session_id=$1 AND status=$2 ORDER BY created_at DESC LIMIT 8) h ORDER BY created_at',body.session_id,'complete')]
    except Exception:
        if lock: await conn.execute('SELECT pg_advisory_unlock(hashtextextended($1,0))',str(body.session_id))
        await p.release(conn)
        raise

    async def stream():
        answer_id=uuid4(); started=time.monotonic(); text=''; sources=[]; persisted=False
        try:
            async with conn.transaction():
                await conn.execute('INSERT INTO messages(id,session_id,role,content,provider,mode) VALUES($1,$2,$3,$4,$5,$6)',uuid4(),body.session_id,'user',body.message,provider,body.mode)
                await conn.execute("UPDATE sessions SET title=CASE WHEN title='New conversation' THEN $2 ELSE title END,updated_at=now() WHERE id=$1",body.session_id,body.message[:80])
            yield sse('status',content='Searching the transcript archive')
            sources=await retrieve(conn,contextual_query(body.message,history))
            event_log('retrieval',request_id=request.state.request_id,count=len(sources),duration_ms=round((time.monotonic()-started)*1000))
            yield sse('sources',sources=sources)
            if not sources:
                text=ABSTENTION
                yield sse('token',content=text)
            else:
                yield sse('status',content='Writing from the retrieved sources')
                async with asyncio.timeout(settings().model_timeout):
                    async with httpx.AsyncClient(timeout=httpx.Timeout(settings().model_timeout,connect=10)) as client:
                        async with client.stream('POST',settings().agent_url+'/generate',json={
                            'provider':provider,'mode':body.mode,'message':body.message,
                            'history':history,'sources':sources,
                        }) as response:
                            response.raise_for_status()
                            async for line in response.aiter_lines():
                                if not line: continue
                                item=json.loads(line)
                                if item['type']=='error': raise RuntimeError('Model generation failed')
                                if item['type']=='replace':
                                    text=item['content']
                                    yield sse('replace',content=text)
                                if item['type']=='status':
                                    yield sse('status',content=item['content'])
                                if item['type']=='token':
                                    if not text: event_log('first_token',request_id=request.state.request_id,ms=round((time.monotonic()-started)*1000))
                                    text+=item['content']
                                    if len(text)>100000: raise RuntimeError('Output limit exceeded')
                                    yield sse('token',content=item['content'])
                if not text.strip(): raise RuntimeError('Model returned an empty answer')
                for warning in validate_citations(text,sources):
                    if 'withheld' in warning: raise RuntimeError('Invalid source citation')
                    if 'did not include' in warning and not re.search(r'do not have sufficient|not enough information|cannot answer',text,re.I):
                        raise RuntimeError('Missing source citations after revision')
                    yield sse('warning',content=warning)
            art=None
            if body.mode!='answer' and sources and not re.search(r'do not have sufficient information|cannot answer',text,re.I):
                content=re.sub(r'^```(?:html|markdown)?\s*\n|\n```\s*$','',text.strip())
                words=len(re.findall(r'\b[\w\u2019-]+\b',content))
                if body.mode=='essay' and not 1100<=words<=1400:
                    yield sse('warning',content=f'Essay is {words} words; target is 1,100–1,400. Ask for a revision to adjust length.')
                art={'id':str(uuid4()),'message_id':str(answer_id),'artifact_type':'html' if body.mode=='html' else 'markdown','title':body.message[:80],'content':content}
            async with conn.transaction():
                await conn.execute('INSERT INTO messages(id,session_id,role,content,sources,provider,mode) VALUES($1,$2,$3,$4,$5,$6,$7)',answer_id,body.session_id,'assistant',text,json.dumps(sources),provider,body.mode)
                if art:
                    await conn.execute('INSERT INTO artifacts(id,message_id,artifact_type,title,content) VALUES($1,$2,$3,$4,$5)',UUID(art['id']),answer_id,art['artifact_type'],art['title'],art['content'])
                await conn.execute('UPDATE sessions SET updated_at=now() WHERE id=$1',body.session_id)
            persisted=True
            if art: yield sse('artifact',artifact=art)
            yield sse('done',message_id=str(answer_id),elapsed_ms=round((time.monotonic()-started)*1000))
        except asyncio.CancelledError:
            event_log('generation_cancelled',request_id=request.state.request_id)
            raise
        except Exception as exc:
            event_log('generation_failed',request_id=request.state.request_id,error=type(exc).__name__)
            yield sse('error',content='Generation could not finish. Check the selected provider and system status, then retry.',request_id=request.state.request_id)
        finally:
            async def cleanup():
                try:
                    if not persisted:
                        await conn.execute('INSERT INTO messages(id,session_id,role,content,sources,provider,mode,status) VALUES($1,$2,$3,$4,$5,$6,$7,$8)',answer_id,body.session_id,'assistant',text or 'Generation interrupted.',json.dumps(sources),provider,body.mode,'failed')
                finally:
                    await conn.execute('SELECT pg_advisory_unlock(hashtextextended($1,0))',str(body.session_id))
                    await p.release(conn)
            await asyncio.shield(cleanup())
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

web_root=Path('/app/web')
if web_root.exists():
    app.mount('/assets', StaticFiles(directory=web_root/'assets'), name='assets')
    @app.get('/{path:path}', include_in_schema=False)
    async def spa(path: str):
        return FileResponse(web_root/'index.html')
