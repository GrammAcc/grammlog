if __name__ != "__main__":
    raise ImportError("Standalone script cannot be imported!")

import http.server
from pathlib import Path

siteroot = Path(Path(__file__).parent, "site")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=siteroot, **kwargs)


server = http.server.HTTPServer(("127.0.0.1", 9000), Handler)
print("Serving API Docs on 127.0.0.1 port 9000 (http://127.0.0.1:9000/) ...")
server.serve_forever()
