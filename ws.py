#!/usr/bin/env python

import sys
import glob, os
import BaseHTTPServer
import SimpleHTTPServer
import SocketServer
import shutil
import urllib
import zipfile
import tempfile
import optparse
import getpass
import base64
import mimetypes
from SocketServer import ThreadingMixIn
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

credentials = () 

def isdir(path):
    path = os.path.join(base_dir, urllib.unquote(path))
    return os.path.isdir(path)

def list_dir(path):
    r = ''
    p = os.path.join(base_dir, urllib.unquote(path))
    if path.find('/') > -1:
        path = '/' + path
    for f in sorted(os.listdir(p)):
        fp = os.path.join(p, f)
        r += '<a href="' + path + '/' + f + '" >' + f + '</a>'
        if os.path.isdir(fp):
             r += ' <a class="dir" href="' + path + '/' + f + '?d=1" >(download dir)</a></br>\n'
        else:
            r += '</br>\n'
    return r

def exists(path):
    path = os.path.join(base_dir, urllib.unquote(path))
    return os.path.exists(path)

def gen_dict(args):
    d = {}
    for arg in args.split(','):
        if arg.find('=') > 0:
            k,v = arg.split('=')
            d[k] = v
    return d

class ThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if len(credentials) == 2:
            if self.headers.getheader('Authorization') != 'Basic ' + credentials[1]:
                self.do_AUTHHEAD()
                self.wfile.write('not authenticated\n')
                return
        args = {}
        self.path = self.path.lstrip('/')
        if self.path.find('?') > -1:
            self.path, args = self.path.split('?')
            args = gen_dict(args)
        if exists(self.path):
            if isdir(self.path):
                if args.has_key('d') and args['d'] == '1':
                    path = urllib.url2pathname(self.path)
                    file_path = os.path.join(base_dir, path)
                    filename = file_path.split('/')[-1] + '.zip'
                    
                    print 'download - ' + str(self.client_address) + ': ' + file_path + ' as ' + filename

                    tmp_zip = tempfile.NamedTemporaryFile()
                    z = zipfile.ZipFile(tmp_zip, mode='w')

                    if path.find(os.sep) > -1:
                        zip_base = path.split(os.sep)[-1]
                    else:
                        zip_base = path

                    for root,dirs,files in os.walk(file_path):
                        for f in files:
                            zip_file = os.path.join(root[root.find(urllib.url2pathname(path)):], f)
                            if zip_base != path:
                                zip_file = zip_file[zip_file.find(zip_base, 1):]
                            z.write(os.path.join(root, f), zip_file)

                    z.close()
                    self.send_response(200)
                    self.send_header('Content-type', 'application/octet-stream')
                    self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
                    self.send_header('Content-length', str(os.path.getsize(tmp_zip.name)))
                    self.end_headers()
                    shutil.copyfileobj(open(tmp_zip.name, 'rb'), self.wfile)
                else:
                    data = """<html>\n<head><meta name="viewport" content="width=device-width, minimumscale=1.0, maximum-scale=1.0" />\n
                    </head>\n<body>\n
                        <style>
                        body {
                            margin: 0;
                            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                            font-size: 14px;
                            line-height: 18px;
                            color: #333333;
                            background-color: #ffffff;
                            padding: 10px;
                        }
                        .dir {
                            font-size: 75%;
                        }
                        </style>"""
                    data += '<b>directory listing for ' + os.path.join(base_dir, urllib.unquote(self.path)) + '</b><hr>'
                    data += list_dir(self.path)
                    data += '</body>\n</html>'
                    self.heads()
                    self.wfile.write(data)
            else:
                self.path = urllib.unquote(self.path)
                print 'download ' + str(self.client_address) + ': ' + self.path
                file_path = os.path.join(base_dir, self.path)
                mimetype = 'application/octet-stream'
                mimetype = mimetypes.guess_type(file_path)
                filename = file_path.split('/')[-1]
                f = open(file_path, 'rb')
                size = os.path.getsize(file_path)
                self.send_response(200)
                self.send_header('Content-type', mimetype)
                # these options force the file to be downloaded no matter what
                #self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
                #self.send_header('Content-length', str(size))
                self.end_headers()
                shutil.copyfileobj(f, self.wfile)
        else:
            if self.path != 'favicon.ico': # ignore requests for a favicon
                print '404:', self.path
                self.heads(response=404)
                self.wfile.write('<h1>404 Not Found</h1>\n')

    def do_AUTHHEAD(self):                  
        self.send_response(401)                             
        self.send_header('WWW-Authenticate', 'Basic realm="ws file share"')
        self.send_header('Content-type', 'text/html')                       
        self.end_headers()  

    def log_request(self, code=None, size=0):
        pass # don't log all requests
    
    def heads(self, response=200, mime='text/html'):
        self.send_response(response)
        self.send_header('Content-type',  mime)
        self.end_headers()
    
if __name__ == '__main__':
    o = optparse.OptionParser()
    o.add_option('-d', dest='directory', default=os.getcwd())
    o.add_option('-P', dest='port', default='8001')
    o.add_option('-u', dest='user', default=None)
    o.add_option('-p', dest='password', default=None)
    options,args = o.parse_args()
    
    base_dir = options.directory
    if not os.path.exists(base_dir):
        sys.exit(base_dir + ' does not exist')
    if options.user:
        if not options.password:
            p1 = getpass.getpass('password: ')
            p2 = getpass.getpass('confirm password: ')
            if p1 == p2:
                options.password = p1
            else:
                sys.exit('Passwords do not match.') 
        credentials = (options.user, base64.b64encode(options.user + ':' + options.password))
    server = ThreadedHTTPServer(('', int(options.port)), Handler)
    server.xxx = False
    print 'sharing ' + options.directory + ' on port ' + options.port
    server.serve_forever()
