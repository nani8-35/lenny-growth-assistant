"""Runs against a dedicated test database, never truncates the application's database."""
import os
from uuid import uuid4
import asyncpg
import pytest
from app.db import initialize

@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_isolation_persistence_and_vector_order():
    url=os.getenv('TEST_DATABASE_URL')
    if not url:pytest.skip('Set TEST_DATABASE_URL for the real PostgreSQL integration test')
    p=await asyncpg.create_pool(url)
    await initialize(p)
    a,b=uuid4(),uuid4();ep='test-'+str(uuid4());msg=uuid4()
    try:
        await p.executemany('INSERT INTO sessions(id,title) VALUES($1,$2)',[(a,'A'),(b,'B')])
        await p.execute("INSERT INTO messages(id,session_id,role,content) VALUES($1,$2,'user','A private question')",msg,a)
        await p.execute("INSERT INTO artifacts(id,message_id,artifact_type,title,content) VALUES($1,$2,'markdown','Draft','# Persisted')",uuid4(),msg)
        await p.close();p=await asyncpg.create_pool(url)
        assert await p.fetchval('SELECT count(*) FROM messages WHERE session_id=$1',a)==1
        assert await p.fetchval('SELECT count(*) FROM messages WHERE session_id=$1',b)==0
        assert await p.fetchval('SELECT content FROM artifacts WHERE message_id=$1',msg)=='# Persisted'
        await p.execute("INSERT INTO episodes(id,title,guest,source_url,checksum,embedding_model) VALUES($1,'t','g','https://example.com','c','test')",ep)
        v1=[1.0]+[0.0]*767;v2=[0.0,1.0]+[0.0]*766
        await p.executemany('INSERT INTO chunks(episode_id,ordinal,content,embedding) VALUES($1,$2,$3,$4::vector)',[(ep,0,'match',str(v1)),(ep,1,'other',str(v2))])
        assert await p.fetchval('SELECT content FROM chunks WHERE episode_id=$1 ORDER BY embedding <=> $2::vector LIMIT 1',ep,str(v1))=='match'
    finally:
        await p.execute('DELETE FROM sessions WHERE id=ANY($1::uuid[])',[a,b]);await p.execute('DELETE FROM episodes WHERE id=$1',ep);await p.close()
