"""Build only generated output; project data and template sources remain intact."""
from pathlib import Path
import html,json,shutil,re
ROOT=Path(__file__).resolve().parents[1]
def build(root=ROOT):
    config=json.loads((root/'project/config.json').read_text())
    topics=json.loads((root/'project/data/topics.json').read_text())
    records=json.loads((root/'project/data/catalog.json').read_text())
    for rows in [topics,records]:
        ids=[row['id'] for row in rows]
        if len(set(ids))!=len(ids) or any(not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',s) for s in ids):raise ValueError('Invalid/duplicate IDs')
    for row in records:
        for key in ['video','poster']:
            value=row.get(key,'')
            if value and (not value.startswith('media/') or '..' in Path(value).parts or ':' in value):raise ValueError('Media must be relative inside media/')
    tabs=config['tabs']
    if [tab['path'] for tab in tabs[:2]]!=['index.html','videos.html']:raise ValueError('Main and videos must be the first tabs')
    if len({t['path'] for t in tabs})!=len(tabs):raise ValueError('Duplicate tabs')
    seconds=config.get('refresh_seconds',15)
    if not isinstance(seconds,int) or seconds<5:raise ValueError('Refresh interval must be at least 5 seconds')
    for tab in tabs:
        if not re.fullmatch(r'[a-zA-Z0-9_-]+\.html',tab['path']) or tab['path']=='topic.html':raise ValueError('Invalid extension tab path')
    dist=root/'dist'
    if dist.is_symlink():raise ValueError('Refuse symlink output')
    stage=root/'.runtime/build';stage.parent.mkdir(exist_ok=True)
    if stage.exists():shutil.rmtree(stage)
    shutil.copytree(root/'template',stage)
    for tab in tabs[2:]:shutil.copyfile(root/'project/tabs'/tab['path'],stage/tab['path'])
    for page in ['index.html','videos.html','topic.html']:
        nav='<div class="nav-tabs" aria-label="페이지 탭">'+''.join(f'<a href="{html.escape(t["path"],quote=True)}"'+(' class="active" aria-current="page"' if t['path']==('videos.html' if page=='topic.html' else page) else '')+'>'+html.escape(t['label'])+'</a>' for t in tabs)+'</div>'
        f=stage/page;s=f.read_text()
        for key,value in {'TITLE':html.escape(config['title']),'BRAND':html.escape(config['title']),'NAV':nav,'RECORDING_NOTE':html.escape(config.get('recording_note','')),'MAIN':(root/'project/main.html').read_text()}.items():s=s.replace('{{'+key+'}}',value)
        settings=json.dumps({'title':config['title'],'refresh_ms':seconds*1000},ensure_ascii=False).replace('<','\\u003c')
        s=s.replace('</head>',f'<script>const pageConfig={settings};window.PAGE_TITLE=pageConfig.title;window.PAGE_REFRESH_MS=pageConfig.refresh_ms;</script></head>');f.write_text(s)
    shutil.copyfile(root/'project/data/topics.json',stage/'topics.json')
    media=stage/'media';media.mkdir();shutil.copyfile(root/'project/data/catalog.json',media/'catalog.json')
    for f in (root/'project/media').rglob('*'):
        if f.is_symlink():raise ValueError('Refuse media symlinks')
        if f.is_file() and not f.name.startswith('.'):
            dest=media/f.relative_to(root/'project/media');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
    if dist.exists():shutil.rmtree(dist)
    stage.rename(dist)
    return dist
if __name__=='__main__':print(build())
