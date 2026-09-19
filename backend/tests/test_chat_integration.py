import json
import os
from uuid import UUID
import asyncpg
import httpx
import pytest
from app import main
from app.db import initialize

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_stream_artifact_followup_failure_and_lock(monkeypatch):
    url=os.getenv('TEST_DATABASE_URL')
    if not url:pytest.skip('Set TEST_DATABASE_URL to run the API persistence integration test')
    pool=await asyncpg.create_pool(url);await initialize(pool)
    monkeypatch.setattr(main.app.state,'pool',pool,raising=False)
    real_client=httpx.AsyncClient
    state={'fail':False,'queries':[]}
    def agent_transport(request):
        if request.url.path=='/health':return httpx.Response(200,json={'cloud_configured':False})
        if state['fail']:return httpx.Response(503,json={'error':'unavailable'})
        return httpx.Response(200,text=json.dumps({'type':'token','content':'# Evidence\n\nA supported point [S1].'})+'\n'+json.dumps({'type':'done'})+'\n')
    monkeypatch.setattr(main.httpx,'AsyncClient',lambda **kwargs:real_client(transport=httpx.MockTransport(agent_transport),**kwargs))
    async def retrieval(conn,query):
        state['queries'].append(query)
        if query=='unsupported':return []
        return [{'id':'S1','content':'A supported point','guest':'Test','title':'Episode','source_url':'https://example.com','timestamp_ref':'00:01','score':.8}]
    monkeypatch.setattr(main,'retrieve',retrieval)
    ids=[]
    try:
        async with real_client(transport=httpx.ASGITransport(app=main.app),base_url='http://test') as client:
            sid=(await client.post('/api/sessions',json={})).json()['id'];ids.append(UUID(sid))
            response=await client.post('/api/chat',json={'session_id':sid,'message':'Explain retention','mode':'markdown'})
            assert response.status_code==200 and '"type": "artifact"' in response.text and '"type": "done"' in response.text
            saved=(await client.get('/api/sessions/'+sid)).json()
            assert len(saved['messages'])==2 and len(saved['artifacts'])==1
            assert saved['messages'][-1]['status']=='complete'
            await client.post('/api/chat',json={'session_id':sid,'message':'Expand that'})
            assert 'Explain retention' in state['queries'][-1]
            other=(await client.post('/api/sessions',json={})).json()['id'];ids.append(UUID(other))
            assert (await client.get('/api/sessions/'+other)).json()['messages']==[]
            cloud=await client.post('/api/chat',json={'session_id':other,'message':'test','provider':'anthropic'})
            assert cloud.status_code==503 and 'No automatic fallback' in cloud.text
            async with pool.acquire() as lock:
                await lock.execute('SELECT pg_advisory_lock(hashtextextended($1,0))',sid)
                assert (await client.post('/api/chat',json={'session_id':sid,'message':'conflict'})).status_code==409
                await lock.execute('SELECT pg_advisory_unlock(hashtextextended($1,0))',sid)
            state['fail']=True
            failure=await client.post('/api/chat',json={'session_id':sid,'message':'model failure'})
            assert '"type": "error"' in failure.text and '"type": "done"' not in failure.text
            saved=(await client.get('/api/sessions/'+sid)).json()
            assert saved['messages'][-1]['status']=='failed'
            abstain=await client.post('/api/chat',json={'session_id':other,'message':'unsupported'})
            assert 'do not have sufficient information' in abstain.text and '"type": "done"' in abstain.text
    finally:
        await pool.execute('DELETE FROM sessions WHERE id=ANY($1::uuid[])',ids)
        await pool.close()
