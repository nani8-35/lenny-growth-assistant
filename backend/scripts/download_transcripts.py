"""Fetch public archive snapshot. Extract only transcript markdown; never execute repository code."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile
import httpx

REPO='ChatPRD/lennys-podcast-transcripts'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='data/transcripts');parser.add_argument('--ref',default='main');args=parser.parse_args()
    root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    with httpx.Client(timeout=180,follow_redirects=True) as client:
        ref=client.get(f'https://api.github.com/repos/{REPO}/commits/{args.ref}');ref.raise_for_status();sha=ref.json()['sha']
        response=client.get(f'https://codeload.github.com/{REPO}/zip/{sha}');response.raise_for_status()
    count=0
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        for entry in archive.infolist():
            parts=Path(entry.filename).parts
            if len(parts)!=4 or parts[1]!='episodes' or parts[-1]!='transcript.md':continue
            if entry.file_size>5_000_000:raise ValueError('Unexpected transcript size')
            dest=root/parts[2]/'transcript.md'
            if not dest.resolve().is_relative_to(root.resolve()):raise ValueError('Unsafe archive path')
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(archive.read(entry));count+=1
    manifest={'repository':f'https://github.com/{REPO}','commit':sha,'archive_sha256':hashlib.sha256(response.content).hexdigest(),'episodes_downloaded':count}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest))
if __name__=='__main__':main()
