"""Check the project/template boundary, rejected updates, and reversible state."""
import unittest,tempfile,shutil,json,hashlib,sys,threading,urllib.request,urllib.error
from pathlib import Path
from functools import partial
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build import build
from update_template import update
from serve import Handler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
class TemplateTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'target';shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('.git','dist','.runtime','__pycache__'))
 def tearDown(self):self.tmp.cleanup()
 def test_project_extensions_and_media_boundary(self):
  config=json.loads((self.root/'project/config.json').read_text());config['tabs'].append({'label':'추가','path':'extra.html'});(self.root/'project/config.json').write_text(json.dumps(config));(self.root/'project/tabs/extra.html').write_text('<h1>Custom tab</h1>')
  (self.root/'project/main.html').write_text('<h1>Project-owned progress</h1>');dist=build(self.root)
  self.assertIn('Project-owned progress',(dist/'index.html').read_text());self.assertIn('extra.html',(dist/'index.html').read_text());self.assertTrue((dist/'extra.html').exists());self.assertFalse((dist/'scripts').exists());self.assertFalse((dist/'.runtime').exists())
 def test_invalid_media_path_rejected(self):
  f=self.root/'project/data/catalog.json';rows=json.loads(f.read_text());rows[0]['video']='../private.mp4';f.write_text(json.dumps(rows))
  with self.assertRaises(ValueError):build(self.root)
 def test_update_preserves_project_and_state(self):
  source=Path(self.tmp.name)/'source';shutil.copytree(self.root,source)
  (self.root/'project/main.html').write_text('USER CONTENT');(self.root/'project/media/user-video.bin').write_bytes(b'USER MEDIA');saved={str(p.relative_to(self.root)):p.read_bytes() for p in (self.root/'project').rglob('*') if p.is_file()};(self.root/'.runtime').mkdir();(self.root/'.runtime/state.json').write_text('USER STATE')
  target=source/'template/style.css';target.write_text(target.read_text()+'\n/* revised common style */\n');manifest=json.loads((source/'template-manifest.json').read_text());manifest['files']['template/style.css']=hashlib.sha256(target.read_bytes()).hexdigest();(source/'template-manifest.json').write_text(json.dumps(manifest))
  old=(self.root/'template/style.css').read_bytes();update(self.root,source);self.assertEqual(old,(self.root/'template/style.css').read_bytes());update(self.root,source,True)
  self.assertEqual('USER CONTENT',(self.root/'project/main.html').read_text());self.assertEqual('USER STATE',(self.root/'.runtime/state.json').read_text());self.assertEqual(target.read_bytes(),(self.root/'template/style.css').read_bytes());self.assertTrue(all((self.root/name).read_bytes()==data for name,data in saved.items()))
 def test_common_modification_stops_without_overwrite(self):
  source=Path(self.tmp.name)/'source';shutil.copytree(self.root,source);p=self.root/'template/index.html';p.write_text('USER CUSTOMIZATION')
  with self.assertRaises(ValueError):update(self.root,source,True)
  self.assertEqual('USER CUSTOMIZATION',p.read_text())
 def test_manifest_cannot_write_project_layer(self):
  source=Path(self.tmp.name)/'source';shutil.copytree(self.root,source);manifest=json.loads((source/'template-manifest.json').read_text());name='project/data/catalog.json';manifest['files'][name]=hashlib.sha256((source/name).read_bytes()).hexdigest();(source/'template-manifest.json').write_text(json.dumps(manifest));before=(self.root/name).read_bytes()
  with self.assertRaises(ValueError):update(self.root,source,True)
  self.assertEqual(before,(self.root/name).read_bytes())
 def test_persistent_delete_restore_and_origin(self):
  dist=build(self.root);Handler.state_file=self.root/'.runtime/board-state.json';server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(dist)));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}'
  before=(self.root/'project/data/topics.json').read_bytes()
  def post(action,origin):
   req=urllib.request.Request(url+'/api/board/'+action,data=json.dumps({'kind':'topic','id':'sample-topic','title':'sample'}).encode(),headers={'Origin':origin,'Content-Type':'application/json'});return json.load(urllib.request.urlopen(req))
  try:
   with self.assertRaises(urllib.error.HTTPError) as error:post('delete','http://different-origin')
   self.assertEqual(error.exception.code,403);self.assertEqual(len(post('delete',url)['deleted']),1);self.assertEqual(len(Handler.state_file.read_text())>0,True);self.assertEqual(post('restore',url)['deleted'],[]);self.assertEqual(before,(self.root/'project/data/topics.json').read_bytes())
  finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
