import io
import logging
import mimetypes
import ntpath
import os
import socket
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from email.parser import Parser
from email.utils import formatdate
from optparse import OptionParser
from urllib.parse import urlparse, unquote

LOG_LEVELS = {
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'ERROR': logging.ERROR
}

MAX_LINE_LENGTH = 64 * 1024
MAX_HEADERS = 100

HttpRequest = namedtuple('HttpRequest', ['method', 'target', 'version', 'header', 'rfile'])
HttpResponse = namedtuple('HttpResponse', ['status', 'reason', 'headers', 'body'])


class HTTPError(Exception):
    def __init__(self, status, reason, body=None):
        super()
        self.status = status
        self.reason = reason
        self.body = body


class WebServer:
    def __init__(self, host, port, document_root, workers):
        self.host = host
        self.port = port
        self.document_root = document_root
        self.workers = int(workers)

    def serve_forever(self):
        serv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, proto=0)
        serv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        pool = ThreadPoolExecutor(self.workers)
        try:
            serv_sock.bind((self.host, self.port))
            serv_sock.listen(self.workers)
            while True:
                conn, addr = serv_sock.accept()
                try:
                    pool.submit(self.serve_client, conn)
                except Exception as e:
                    logging.error('Client serving failed', e)
        finally:
            pool.shutdown()
            serv_sock.close()

    def serve_client(self, conn):
        try:
            request = self.parse_request(conn)
            response = self.handle_request(request)
            self.send_response(conn, response)
        except ConnectionResetError as e:
            logging.error(str(e))
            conn = None
        except HTTPError as e:
            logging.error(str(e))
            self.send_error(conn, e)

        if conn:
            conn.close()

    def parse_request(self, conn):
        rfile = conn.makefile('rb')
        raw = rfile.readline(MAX_LINE_LENGTH + 1)
        if len(raw) > MAX_LINE_LENGTH:
            raise HTTPError(400, 'Request line is too long')

        req_line = str(raw, 'iso-8859-1')
        req_line = req_line.rstrip('\r\n')
        words = req_line.split()
        if len(words) != 3:
            logging.error('Malformed request line')

        method, target, ver = words

        headers = self.parse_headers(rfile)
        host = headers.get('Host')
        if not host:
            logging.error('Host undefined')

        return HttpRequest(method, target, None, None, None)

    def parse_headers(self, rfile):
        headers = []
        while True:
            line = rfile.readline(MAX_LINE_LENGTH + 1)
            if len(line) > MAX_LINE_LENGTH:
                raise HTTPError(400, 'Header line is too long')

            if line in (b'\r\n', b'\n', b''):
                break

            headers.append(line)
            if len(headers) > MAX_HEADERS:
                raise HTTPError(400, 'Too many headers')

        headers = b''.join(headers).decode('iso-8859-1')
        return Parser().parsestr(headers)

    def handle_request(self, request):
        headers = {
            'Date': formatdate(timeval=None, localtime=False, usegmt=True),
            'Connection': 'close',
            'Server': 'WebServer/1.0',
            'Content-Length': 0
        }
        if request.method in ['GET', 'HEAD']:
            file, file_name = self.get_file(request.target)
            if file:
                ctype = mimetypes.MimeTypes().guess_type(file_name)[0]
                headers['Content-type'] = ctype
                headers['Content-Length'] = len(file.getbuffer())
                if request.method == 'GET':
                    return HttpResponse(200, 'OK', headers, file)
                else:
                    file.close()
                return HttpResponse(200, 'OK', headers, None)

            return HttpResponse(404, 'File not found', headers, None)

        return HttpResponse(405, 'Method not allowed', headers, None)

    def get_file(self, target):
        path = self.get_path(target)
        if self.document_root not in path:
            return None, None
        if os.path.isdir(path):
            list_dir = os.listdir(path)
            if "index.html" in list_dir:
                path = os.path.join(path, "index.html")
            else:
                return None, None
        if os.path.isfile(path):
            f = open(path, 'rb')
            return io.BytesIO(f.read()), ntpath.basename(path)
        return None, None

    def get_path(self, target):
        path = unquote(urlparse(target).path)
        if path == '/':
            return self.document_root
        full_path = os.path.join(self.document_root, path.strip(os.sep))
        return os.path.realpath(full_path)

    def send_response(self, conn, resp):
        wfile = conn.makefile('wb')
        status_line = f'HTTP/1.1 {resp.status} {resp.reason}\r\n'
        wfile.write(status_line.encode('iso-8859-1'))

        if resp.headers:
            for (key, value) in resp.headers.items():
                header_line = f'{key}: {value}\r\n'
                wfile.write(header_line.encode('iso-8859-1'))

        wfile.write(b'\r\n')

        if resp.body:
            body_value = resp.body.getvalue() if isinstance(resp.body, io.BytesIO) else resp.body
            wfile.write(body_value)

        wfile.flush()
        wfile.close()

    def send_error(self, conn, err):
        try:
            status = err.status
            reason = err.reason
            body = (err.body or err.reason).encode('utf-8')
        except:
            status = 500
            reason = b'Internal Server Error'
            body = b'Internal Server Error'
        resp = HttpResponse(status, reason, {'Content-Length': len(body)}, body)
        self.send_response(conn, resp)


def main():
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-a", "--address", action="store", type=str, default='localhost')
    op.add_option("-w", "--workers", action="store", type=int, default=1)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("-e", "--log_level", action="store", default='INFO')
    op.add_option("-r", "--root", action="store", default=os.getcwd())
    opts, _ = op.parse_args()

    logging.basicConfig(filename=opts.log, level=LOG_LEVELS.get(opts.log_level, 'INFO'),
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')

    server = WebServer(opts.address, opts.port, opts.root, opts.workers)
    try:
        logging.info("Starting server at %s" % opts.port)
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
