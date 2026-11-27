import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from lennar_source_retry import configure_source_session

class Handler(BaseHTTPRequestHandler):
    counts={}
    def do_GET(self):
        n=self.counts.get(self.path,0)+1
        self.counts[self.path]=n
        code=503 if self.path=="/outage" or (self.path=="/recover" and n<3) else 404 if self.path=="/missing" else 200
        self.send_response(code)
        self.end_headers()
    def log_message(self,*args): pass

server=HTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with configure_source_session(requests.Session()) as session:
        session.mount("http://",session.get_adapter("https://"))
        base="http://127.0.0.1:"+str(server.server_port)
        assert session.get(base+"/recover",timeout=5).status_code==200
        assert Handler.counts["/recover"]==3
        assert session.get(base+"/outage",timeout=5).status_code==503
        assert Handler.counts["/outage"]==3
        assert session.get(base+"/missing",timeout=5).status_code==404
        assert Handler.counts["/missing"]==1
        print("PASS transient recovery, bounded outage, permanent HTTP error")
finally:
    server.shutdown()
    server.server_close()
