"""Record common-file hashes after reviewing a template release."""
from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parents[1]
files=[r/'VERSION.json']+[p for folder in ['template','scripts'] for p in (r/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
manifest={'version':json.loads((r/'VERSION.json').read_text())['version'],'files':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}}
(r/'template-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
