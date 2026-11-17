"""Serve generated output on loopback and persist only reversible visibility state."""
import argparse,json,re,threading
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from datetime import datetime,timezone
class Handler(SimpleHTTPRequestHandler):
    state_file=None
    state_lock=threading.Lock()
    def read_state(self):return json.loads(self.state_file.read_text()) if self.state_file.exists() else {'deleted':[]}
    def respond(self,status,data):
        body=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/api/board':
            with self.state_lock:self.respond(200,self.read_state())
        elif any(part.startswith('.') for part in path.split('/')):self.send_error(404)
        else:super().do_GET()
    def do_POST(self):
        if self.path not in {'/api/board/delete','/api/board/restore'}:return self.respond(404,{'error':'Unknown operation'})
        if self.headers.get('Origin')!='http://'+self.headers.get('Host',''):return self.respond(403,{'error':'Same origin required'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=4096:raise ValueError()
            data=json.loads(self.rfile.read(length));kind=data.get('kind');identity=data.get('id','');title=data.get('title',identity)
            if kind not in {'topic','video'} or not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',identity) or not isinstance(title,str) or len(title)>300:raise ValueError()
            file=Path(self.directory)/('topics.json' if kind=='topic' else 'media/catalog.json')
            if identity not in {row['id'] for row in json.loads(file.read_text())}:raise ValueError()
        except (ValueError,TypeError,AttributeError):return self.respond(400,{'error':'Invalid item'})
        with self.state_lock:
            state=self.read_state();state['deleted']=[r for r in state['deleted'] if (r['kind'],r['id'])!=(kind,identity)]
            if self.path.endswith('/delete'):state['deleted'].append({'kind':kind,'id':identity,'title':title,'deleted_at':datetime.now(timezone.utc).isoformat()})
            self.state_file.parent.mkdir(parents=True,exist_ok=True);temp=self.state_file.with_suffix('.tmp');temp.write_text(json.dumps(state,ensure_ascii=False,indent=2));temp.replace(self.state_file);self.respond(200,state)
def main():
    root=Path(__file__).resolve().parents[1];parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8910);args=parser.parse_args()
    Handler.state_file=root/'.runtime/board-state.json'
    if not (root/'dist/index.html').is_file():parser.error('Run scripts/build.py first')
    ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,directory=str(root/'dist'))).serve_forever()
if __name__=='__main__':main()
