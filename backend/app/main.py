import asyncio
import json
import logging
import re
import time
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from uuid import UUID, uuid4
import httpx
import asyncpg
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
        await ensure_admin(app.state.pool)
    except Exception as exc:
        event_log('database_startup_failed', error=type(exc).__name__)
    yield
    if app.state.pool:
        await app.state.pool.close()

app = FastAPI(title='Lenny Growth Assistant', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings().cors_origin], allow_methods=['GET','POST','DELETE'], allow_headers=['Content-Type','Authorization'])

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
            await ensure_admin(app.state.pool)
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

def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.urlsafe_b64encode(salt).decode()+'.'+base64.urlsafe_b64encode(digest).decode()

def password_matches(password: str, encoded: str) -> bool:
    try:
        salt_value, digest_value = encoded.split('.', 1)
        actual = hash_password(password, base64.urlsafe_b64decode(salt_value.encode())).split('.', 1)[1]
        return hmac.compare_digest(actual, digest_value)
    except Exception:
        return False

def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

async def ensure_admin(pool):
    config=settings(); email=config.admin_email.strip().lower()
    if not email or not config.admin_password: return
    existing=await pool.fetchrow('SELECT id FROM users WHERE email=$1', email)
    if existing:
        await pool.execute('UPDATE users SET is_admin=TRUE WHERE id=$1', existing['id'])
    else:
        await pool.execute('INSERT INTO users(id,email,name,password_hash,is_admin) VALUES($1,$2,$3,$4,TRUE)',uuid4(),email,'Master administrator',hash_password(config.admin_password))

def bearer_token(request: Request) -> str:
    value=request.headers.get('Authorization','')
    if not value.startswith('Bearer '): raise HTTPException(401,'Sign in is required.')
    token=value[7:].strip()
    if len(token)<32: raise HTTPException(401,'Sign in is required.')
    return token

async def current_user(request: Request, pool):
    token=bearer_token(request)
    row=await pool.fetchrow('SELECT u.id,u.email,u.name,u.is_admin FROM auth_sessions a JOIN users u ON u.id=a.user_id WHERE a.token_hash=$1 AND a.expires_at>now()',token_digest(token))
    if not row: raise HTTPException(401,'Your session has expired. Sign in again.')
    return row

async def issue_session(pool, user_id: UUID) -> str:
    token=secrets.token_urlsafe(32)
    await pool.execute('INSERT INTO auth_sessions(token_hash,user_id,expires_at) VALUES($1,$2,$3)',token_digest(token),user_id,datetime.now(timezone.utc)+timedelta(days=settings().session_days))
    return token

class Register(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=200)

class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=200)

async def auth_response(pool, user):
    token=await issue_session(pool,user['id'])
    return {'access_token':token,'user':{'id':str(user['id']),'email':user['email'],'name':user['name'],'is_admin':user['is_admin']}}

@app.post('/api/auth/signup', status_code=201)
async def signup(body: Register):
    email=body.email.strip().lower()
    if '@' not in email: raise HTTPException(422,'Enter a valid email address.')
    p=await get_pool()
    try:
        user=await p.fetchrow('INSERT INTO users(id,email,name,password_hash) VALUES($1,$2,$3,$4) RETURNING id,email,name,is_admin',uuid4(),email,body.name.strip(),hash_password(body.password))
    except asyncpg.UniqueViolationError:
        raise HTTPException(409,'An account already exists for this email.')
    return await auth_response(p,user)

@app.post('/api/auth/login')
async def login(body: Credentials):
    p=await get_pool(); user=await p.fetchrow('SELECT id,email,name,password_hash,is_admin FROM users WHERE email=$1',body.email.strip().lower())
    if not user or not password_matches(body.password,user['password_hash']): raise HTTPException(401,'Email or password is incorrect.')
    return await auth_response(p,user)

@app.post('/api/auth/logout')
async def logout(request: Request):
    p=await get_pool(); token=bearer_token(request); await p.execute('DELETE FROM auth_sessions WHERE token_hash=$1',token_digest(token))
    return {'ok':True}

@app.get('/api/auth/me')
async def me(request: Request):
    p=await get_pool(); user=await current_user(request,p)
    return {'id':str(user['id']),'email':user['email'],'name':user['name'],'is_admin':user['is_admin']}

@app.get('/api/admin/users')
async def users_admin(request: Request):
    p=await get_pool(); user=await current_user(request,p)
    if not user['is_admin']: raise HTTPException(403,'Administrator access is required.')
    rows=await p.fetch('SELECT u.id,u.name,u.email,u.is_admin,u.created_at,count(s.id)::int AS conversation_count FROM users u LEFT JOIN sessions s ON s.user_id=u.id GROUP BY u.id ORDER BY u.created_at DESC')
    return [serialize(row) for row in rows]

@app.post('/api/sessions', status_code=201)
async def create_session(body: NewSession, request: Request):
    p=await get_pool(); user=await current_user(request,p)
    row=await p.fetchrow('INSERT INTO sessions(id,title,user_metadata,user_id) VALUES($1,$2,$3,$4) RETURNING *',uuid4(),body.title,json.dumps(body.user_metadata),user['id'])
    return serialize(row)

@app.get('/api/sessions')
async def sessions(request: Request):
    p=await get_pool(); user=await current_user(request,p)
    return [serialize(r) for r in await p.fetch('SELECT * FROM sessions WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 100',user['id'])]

@app.get('/api/sessions/{session_id}')
async def session(session_id: UUID, request: Request):
    p=await get_pool(); user=await current_user(request,p)
    row=await p.fetchrow('SELECT * FROM sessions WHERE id=$1 AND user_id=$2',session_id,user['id'])
    if not row: raise HTTPException(404,'Conversation not found')
    messages=[serialize(r) for r in await p.fetch('SELECT * FROM messages WHERE session_id=$1 ORDER BY created_at,id',session_id)]
    arts=[serialize(r) for r in await p.fetch('SELECT a.* FROM artifacts a JOIN messages m ON a.message_id=m.id WHERE m.session_id=$1 ORDER BY a.created_at',session_id)]
    return {**serialize(row),'messages':messages,'artifacts':arts}

@app.get('/api/artifacts/{artifact_id}')
async def artifact(artifact_id: UUID, request: Request):
    p=await get_pool(); user=await current_user(request,p)
    row=await p.fetchrow('SELECT a.* FROM artifacts a JOIN messages m ON m.id=a.message_id JOIN sessions s ON s.id=m.session_id WHERE a.id=$1 AND s.user_id=$2',artifact_id,user['id'])
    if not row: raise HTTPException(404,'Artifact not found')
    return serialize(row)

@app.delete('/api/sessions/{session_id}', status_code=204)
async def delete_session(session_id: UUID, request: Request):
    p=await get_pool(); user=await current_user(request,p)
    deleted=await p.execute('DELETE FROM sessions WHERE id=$1 AND user_id=$2',session_id,user['id'])
    if deleted.endswith('0'): raise HTTPException(404,'Conversation not found')
    return None

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
    if not body.message.strip(): raise HTTPException(422,'Enter a question')
    provider=body.provider or settings().default_llm_provider
    p=await get_pool(); user=await current_user(request,p)
    conn=await p.acquire()
    lock=False
    try:
        lock=await conn.fetchval('SELECT pg_try_advisory_lock(hashtextextended($1,0))',str(body.session_id))
        if not lock: raise HTTPException(409,'This conversation is already generating a response')
        if not await conn.fetchval('SELECT 1 FROM sessions WHERE id=$1 AND user_id=$2',body.session_id,user['id']):
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
