#!/usr/bin/env python3
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver

PORT = 8000
DIRECTORY = os.getcwd() + os.sep + 'public'

class Handler(SimpleHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, directory=DIRECTORY, **kwargs)

Handler.extensions_map = {
	'.html': 'text/html',
	'.png': 'image/png',
	'.jpg': 'image/jpg',
	'.svg':	'image/svg+xml',
	'.css':	'text/css',
	'.js':	'text/javascript',
	'.json': 'application/json',
	'.xml': 'text/xml',
	'': 'application/octet-stream',
}

httpd = socketserver.TCPServer(('', PORT), Handler)

print('Running on port', PORT)
httpd.serve_forever()
