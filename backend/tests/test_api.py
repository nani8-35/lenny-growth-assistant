from uuid import uuid4
import pytest
from httpx import ASGITransport,AsyncClient
from app.main import app,sse

@pytest.mark.asyncio
async def test_invalid_inputs_are_rejected_before_services():
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as c:
        for body in [dict(session_id='bad',message='hello'),dict(session_id=str(uuid4()),message=''),dict(session_id=str(uuid4()),message='hi',provider='untrusted'),dict(session_id=str(uuid4()),message='hi',mode='execute')]:
            assert (await c.post('/api/chat',json=body)).status_code==422
        assert (await c.post('/api/sessions',json={'title':'x'*121})).status_code==422

def test_sse_is_safe_for_multiline_and_quotes():
    import json
    text='line one\n"line two"\n\ndata: injected'
    wire=sse('token',content=text)
    assert wire.count('\n\n')==1
    assert json.loads(wire[6:])['content']==text

def test_password_hashing_is_salted_and_verifiable():
    from app.main import hash_password, password_matches
    first=hash_password('A-long-test-password-123')
    second=hash_password('A-long-test-password-123')
    assert first != second
    assert password_matches('A-long-test-password-123', first)
    assert not password_matches('wrong-password', first)
