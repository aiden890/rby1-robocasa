"""Apply a reviewed local template version without modifying any project files."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def allowed(name):return name=='VERSION.json' or (name.startswith(('template/','scripts/')) and '..' not in Path(name).parts and not Path(name).is_absolute())
def update(target,source,apply=False):
    target=target.resolve();source=source.resolve()
    if target==source:raise ValueError('Source and target must differ')
    old=json.loads((target/'template-manifest.json').read_text());new=json.loads((source/'template-manifest.json').read_text())
    for data,root in [(old,target),(new,source)]:
        if any(not allowed(name) for name in data['files']):raise ValueError('Manifest outside template layer')
        for name,sha in data['files'].items():
            f=root/name
            if root not in f.resolve().parents or f.is_symlink() or not f.is_file() or digest(f)!=sha:raise ValueError('Modified/unverified common file: '+name)
    observed={str(f.relative_to(target)) for folder in ['template','scripts'] for f in (target/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts}
    if observed-set(old['files']):raise ValueError('Untracked common customization')
    for name in new['files']:
        if name not in old['files'] and (target/name).exists():raise ValueError('New file conflict: '+name)
    plan=sorted(set(old['files'])|set(new['files']))
    if apply:
        for name in plan:
            f=target/name
            if name in new['files']:f.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,f)
            else:f.unlink()
        shutil.copyfile(source/'template-manifest.json',target/'template-manifest.json')
    return plan
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True,type=Path);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    for name in update(ROOT,args.source,args.apply):print(name)
    print('Applied' if args.apply else 'Dry run only; review diff before --apply')
