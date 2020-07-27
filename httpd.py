import logging
import socket
from collections import namedtuple
from email.parser import Parser
from optparse import OptionParser
import traceback

LOG_LEVELS = {
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'ERROR': logging.ERROR
}

MAX_LINE_LENGTH = 64 * 1024
MAX_HEADERS = 100

Request = namedtuple('Request', ['method', 'target', 'version', 'header' 'rfile'])
Response = namedtuple('Response', ['status', 'reason', 'headers', 'body'])


class HTTPError(Exception):
    def __init__(self, status, reason, body=None):
        super()
        self.status = status
        self.reason = reason
        self.body = body


class WebServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def serve_forever(self):
        serv_sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
            proto=0)

        try:
            serv_sock.bind((self.host, self.port))
            serv_sock.listen()

            while True:
                conn, addr = serv_sock.accept()
                logging.debug(f'Client connected from {addr[0]}:{addr[1]}')
                try:
                    self.serve_client(conn)
                except Exception as e:
                    print('Client serving failed', e)
        finally:
            serv_sock.close()

    def serve_client(self, conn):
        try:
            request = self.parse_request(conn)
            response = self.handle_request(request)
            self.send_response(conn, response)
        except ConnectionResetError as e:
            logging.error(str(e))
            conn = None
        except Exception as e:
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
            raise HTTPError(400, 'Malformed request line')

        method, target, ver = words
        if ver != 'HTTP/1.1':
            raise HTTPError(400, 'Unexpected HTTP version')

        headers = self.parse_headers(rfile)
        host = headers.get('Host')
        if not host:
            raise HTTPError(400, 'Bad request')

        return Request(method, target, ver, headers, rfile)

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
        if request.method in ['GET', 'HEAD']:
            return Response(200, 'OK', [], None)

        return Response(405, 'Method not allowed', [], None)

    def send_response(self, conn, resp):
        wfile = conn.makefile('wb')
        status_line = f'HTTP/1.1 {resp.status} {resp.reason}\r\n'
        wfile.write(status_line.encode('iso-8859-1'))

        if resp.headers:
            for (key, value) in resp.headers:
                header_line = f'{key}: {value}\r\n'
                wfile.write(header_line.encode('iso-8859-1'))

        wfile.write(b'\r\n')

        if resp.body:
            wfile.write(resp.body)

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
        resp = Response(status, reason, [('Content-Length', len(body))], body)
        self.send_response(conn, resp)


def main():
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-a", "--address", action="store", type=str, default='localhost')
    op.add_option("-w", "--workers", action="store", type=int, default=1)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("-e", "--log_level", action="store", default='INFO')
    opts, _ = op.parse_args()

    logging.basicConfig(filename=opts.log, level=LOG_LEVELS.get(opts.log_level, 'INFO'),
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')

    server = WebServer(opts.address, opts.port)
    try:
        logging.info("Starting server at %s" % opts.port)
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
