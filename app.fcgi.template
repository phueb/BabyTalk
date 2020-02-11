#!/usr/local/bin/python

from flup.server.fcgi import WSGIServer
import sys
sys.path.insert(0, 'venv/lib/python2.6/site-packages/')

from src.app import app


class ScriptNameStripper(object):
    def __init__(self, app, script_name):
        self.app = app
        self.script_name = script_name

    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = self.script_name
        return self.app(environ, start_response)


if __name__ == '__main__':
    app = ScriptNameStripper(app, '/babytalk')  # this works
    WSGIServer(app).run()