import re
import httpx
from .config import settings

ABSTENTION = "I do not have sufficient information in Lenny's podcast archive to answer this. Try a question about product strategy, growth, retention, or leadership."

async def embed(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f'{settings().ollama_base_url}/api/embed', json={
            'model': settings().embedding_model, 'input': texts, 'truncate': False,
        })
        r.raise_for_status()
        vectors = r.json()['embeddings']
        if len(vectors) != len(texts) or any(len(v) != 768 for v in vectors):
            raise ValueError('Embedding model must return 768-dimensional vectors')
        return vectors

def contextual_query(question: str, history: list[dict]) -> str:
    previous = [m['content'] for m in history if m['role'] == 'user'][-2:]
    # Only short/anaphoric follow-ups borrow prior topic; unrelated new questions stay independent.
    followup = re.search(r'\b(that|those|this|it|they|their|above|same|turn|expand|more)\b', question, re.I)
    return '\n'.join(previous + [question])[-4000:] if previous and followup else question

async def retrieve(conn, query: str) -> list[dict]:
    if settings().retrieval_mode == 'lexical':
        rows = await conn.fetch('''
          SELECT c.id,c.content,c.timestamp_ref,e.title,e.guest,e.source_url,
                 ts_rank_cd(to_tsvector('english', c.content), websearch_to_tsquery('english', $1)) AS score
          FROM chunks c JOIN episodes e ON e.id=c.episode_id
          WHERE to_tsvector('english', c.content) @@ websearch_to_tsquery('english', $1)
          ORDER BY score DESC LIMIT 24
        ''', query)
        selected, counts = [], {}
        for row in rows:
            key=row['source_url']
            if counts.get(key,0)>=2: continue
            counts[key]=counts.get(key,0)+1
            selected.append({**dict(row),'id':f'S{len(selected)+1}','chunk_id':row['id']})
            if len(selected)>=settings().top_k: break
        return selected
    vector = (await embed([f'search_query: {query}']))[0]
    rows = await conn.fetch('''
      SELECT c.id, c.content, c.timestamp_ref, e.title, e.guest, e.source_url,
             1-(c.embedding <=> $1::vector) AS score
      FROM chunks c JOIN episodes e ON e.id=c.episode_id
      WHERE e.embedding_model=$2
      ORDER BY c.embedding <=> $1::vector LIMIT 24
    ''', str(vector), settings().embedding_model)
    selected, counts = [], {}
    for row in rows:
        if row['score'] < settings().retrieval_threshold:
            continue
        key = row['source_url']
        if counts.get(key, 0) >= 2:
            continue
        counts[key] = counts.get(key, 0) + 1
        selected.append({**dict(row), 'id': f'S{len(selected)+1}', 'chunk_id': row['id']})
        if len(selected) >= settings().top_k:
            break
    return selected

def validate_citations(content: str, sources: list[dict]) -> list[str]:
    valid = {s['id'] for s in sources}
    used = set(re.findall(r'\[(S\d+)\]', content))
    warnings = []
    if not used:
        warnings.append('The model did not include inline citations. Verify this draft against the source cards.')
    if used - valid:
        warnings.append('The model referenced an unknown source. This response was withheld.')
    return warnings
