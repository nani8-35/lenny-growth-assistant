import pytest
from app.retrieval import contextual_query,validate_citations,retrieve
from scripts.ingest import chunk_text,parse_transcript

def test_chunking_preserves_tail_and_bounds():
    text='Speaker (00:01:23): '+('A useful product insight. '*600)+'UNIQUE_END'
    chunks=chunk_text(text)
    assert len(chunks)>1
    assert all(len(c['content'])<=2400 for c in chunks)
    assert chunks[-1]['content'].endswith('UNIQUE_END')
    assert chunks[0]['timestamp_ref']=='00:01:23'
    assert chunks[0]['content'][-300:] in chunks[1]['content']

def test_metadata_and_missing_frontmatter():
    meta,body=parse_transcript('---\nguest: Test Guest\ntitle: Test title\npublish_date: 2025-01-02\n---\nactual text')
    assert meta['guest']=='Test Guest' and meta['published']=='2025-01-02'
    assert body=='actual text'
    assert parse_transcript('plain transcript','Fallback')[0]['guest']=='Fallback'

def test_followup_context_does_not_leak_into_new_question():
    history=[{'role':'user','content':'How do growth loops work?'}]
    assert 'growth loops' in contextual_query('How would I apply that?',history)
    assert contextual_query('What is the weather today?',history)=='What is the weather today?'

def test_citation_validation():
    assert validate_citations('A claim [S1]',[{'id':'S1'}])==[]
    assert 'withheld' in validate_citations('A claim [S9]',[{'id':'S1'}])[0]
    assert validate_citations('No reference',[{'id':'S1'}])

@pytest.mark.asyncio
async def test_threshold_and_episode_diversity(monkeypatch):
    async def fake_embed(_):return [[0.1]*768]
    monkeypatch.setattr('app.retrieval.embed',fake_embed)
    class Conn:
        async def fetch(self,*args):
            return [dict(id=i,content='text',timestamp_ref=None,title='title',guest='guest',source_url='same' if i<4 else 'other',score=.9 if i<5 else .1) for i in range(6)]
    result=await retrieve(Conn(),'growth')
    assert len(result)==3
    assert [r['id'] for r in result]==['S1','S2','S3']
