"""Test image entrypoint: controlled TLS endpoint alongside production proxy."""
import asyncio
import http.server
import ssl
import socket
import sys
import threading
import base64
import hashlib
import time
import json

sys.path.insert(0, '/opt/sandbox-egress')
import proxy

# A deterministic test resolver supplies only the policy's explicit loopback
# exception. Production proxy resolution/address validation still runs in full.
# Provider hosts, including denied optional ones, resolve to the local fixture.
ACCOUNT_HOSTS = ('api.openai.com', 'auth.openai.com', 'chatgpt.com', 'ab.chatgpt.com', 'platform.openai.com')
original_resolver = socket.getaddrinfo
def fixture_resolver(host, port, *args, **kwargs):
    return original_resolver('127.0.0.1' if host in ('localhost.localdomain', 'alternate.test', *ACCOUNT_HOSTS) else host,
                             8443 if host in ACCOUNT_HOSTS else port, *args, **kwargs)
socket.getaddrinfo = fixture_resolver


counts = []
counts_lock = threading.Lock()


HELLO_RETRY_RANDOM = bytes.fromhex('cf21ad74e59a6111be1d8c021e65b891c2a211167abb8c5e079e09e2c8a8339c')


def first_flight(name, curve=None):
    context = ssl.create_default_context(cafile='/test/cert.pem')
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    if curve:
        context.set_ecdh_curve(curve)
    outgoing = ssl.MemoryBIO()
    client = context.wrap_bio(ssl.MemoryBIO(), outgoing, server_hostname=name)
    try:
        client.do_handshake()
    except ssl.SSLWantReadError:
        pass
    return outgoing.read()


def retry_switch(address):
    """Send a retried ClientHello naming alternate.test; report what the server answered."""
    with socket.create_connection(address, timeout=5) as raw:
        raw.sendall(first_flight('localhost.localdomain'))
        received = b''
        while len(received) < 5 or len(received) < 5 + int.from_bytes(received[3:5], 'big'):
            part = raw.recv(16384)
            assert part, 'no HelloRetryRequest'
            received += part
        assert received[11:43] == HELLO_RETRY_RANDOM, 'no HelloRetryRequest'
        raw.sendall(b'\x14\x03\x03\x00\x01\x01' + first_flight('alternate.test', 'prime256v1'))
        later = received[5 + int.from_bytes(received[3:5], 'big'):]
        while True:
            # Skip the server's compatibility ChangeCipherSpec records.
            while later[:6] == b'\x14\x03\x03\x00\x01\x01':
                later = later[6:]
            if len(later) >= 6:
                return 'serverhello' if later[0] == 22 and later[5] == 2 else 'other'
            try:
                part = raw.recv(16384)
            except ConnectionResetError:
                part = b''
            if not part:
                return 'closed' if not later else 'other'
            later += part


class Endpoint(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/alternate-control':
            control_context = ssl.create_default_context(cafile='/test/cert.pem')
            with socket.create_connection(('127.0.0.1', 8443), timeout=5) as raw:
                with control_context.wrap_socket(raw, server_hostname='alternate.test') as secure:
                    secure.sendall(b'GET / HTTP/1.1\r\nHost: alternate.test\r\nConnection: close\r\n\r\n')
                    assert secure.recv(1024).startswith(b'HTTP/1.0 200')
            body = b'alternate-verified-control-ok'
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == '/retry-switch-control':
            # Unfiltered positive control: this OpenSSL server answers a retried
            # ClientHello that names another host after its HelloRetryRequest.
            body = b'retry-switch-control-' + retry_switch(('127.0.0.1', 8443)).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == '/counts':
            with counts_lock:
                body = json.dumps(counts).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', 'https://unapproved.test/?token=fixture-secret-token')
            self.end_headers()
            return
        if self.path == '/websocket':
            self.send_response(101)
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            key = self.headers['Sec-WebSocket-Key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
            self.send_header('Sec-WebSocket-Accept', base64.b64encode(hashlib.sha1(key.encode()).digest()).decode())
            self.end_headers()
            self.wfile.write(b'\x81\x02ok')
            return
        if self.path == '/large':
            body = b'large-frame-boundary-' * 65536
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == '/long-stream':
            self.send_response(200)
            self.send_header('Content-Length', str(75 * len(b'progress\n')))
            self.end_headers()
            for _ in range(75):
                self.wfile.write(b'progress\n')
                self.wfile.flush()
                time.sleep(.2)
            return
        if self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-Length', '3')
            self.end_headers()
            for part in (b'a', b'b', b'c'):
                self.wfile.write(part)
                self.wfile.flush()
                time.sleep(0.2)
            return
        body = b'controlled-production-proxy-ok'
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Synthetic Responses API only: no real model or credentials are used.
        size = int(self.headers.get('Content-Length', '0'))
        if not 0 < size <= 8 * 1024 * 1024:
            self.send_error(400)
            return
        request = json.loads(self.rfile.read(size))
        if not self.path.startswith('/v1/responses'):
            self.send_error(404)
            return
        call_id = 'call_fixture_shell'
        results = [item for item in request.get('input', []) if isinstance(item, dict)
                   and item.get('type') == 'function_call_output' and item.get('call_id') == call_id]
        tools = {tool.get('name') for tool in request.get('tools', []) if isinstance(tool, dict)}
        command = ("python3 -c \"import socket,errno;\ntry: socket.socket(socket.AF_UNIX)\n"
                   "except OSError as e: assert e.errno==errno.EPERM\nelse: raise AssertionError('tool escaped')\" "
                   "&& printf actual-codex-tool-ok > codex-tool-sentinel")
        if not results and 'exec_command' in tools:
            item = {'type': 'function_call', 'name': 'exec_command', 'call_id': call_id,
                    'arguments': json.dumps({'cmd': command})}
        elif not results and 'shell_command' in tools:
            item = {'type': 'function_call', 'name': 'shell_command', 'call_id': call_id,
                    'arguments': json.dumps({'command': command})}
        elif not results and 'shell' in tools:
            item = {'type': 'function_call', 'name': 'shell', 'call_id': call_id,
                    'arguments': json.dumps({'command': ['bash', '-lc', command]})}
        else:
            text = 'fixture-tool-complete' if results else 'fixture-no-shell-tool:' + ','.join(sorted(map(str, tools)))
            item = {'type': 'message', 'role': 'assistant', 'id': 'msg_fixture',
                    'content': [{'type': 'output_text', 'text': text, 'annotations': []}]}
        response = {'id': 'resp_fixture', 'object': 'response', 'status': 'completed', 'output': [item],
                    'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2,
                              'input_tokens_details': {'cached_tokens': 0},
                              'output_tokens_details': {'reasoning_tokens': 0}}}
        events = [('response.created', {'response': {'id': 'resp_fixture', 'status': 'in_progress'}}),
                  ('response.output_item.added', {'output_index': 0, 'item': item}),
                  ('response.output_item.done', {'output_index': 0, 'item': item}),
                  ('response.completed', {'response': response})]
        body = b''.join(('event: ' + event + '\ndata: ' + json.dumps({'type': event, **data}) + '\n\n').encode()
                        for event, data in events)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('x-request-id', 'synthetic-request')
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def log_message(self, *args):
        pass


class TLSFixtureServer(http.server.ThreadingHTTPServer):
    # The budget regression deliberately keeps MAX_STREAMS handshakes active.
    request_queue_size = 128

    def process_request_thread(self, request, address):
        try:
            request.settimeout(12)
            initial = request.recv(16384, socket.MSG_PEEK)
            with counts_lock:
                counts.append(len(initial))
            if not initial:
                return
            secure = context.wrap_socket(request, server_side=True)
            super().process_request_thread(secure, address)
        except (OSError, ssl.SSLError):
            pass
        finally:
            request.close()


server = TLSFixtureServer(('127.0.0.1', 8443), Endpoint)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('/test/cert.pem', '/test/key.pem')
# A supported curve absent from the client's initial key share exercises TLS 1.3 HRR.
context.set_ecdh_curve('prime256v1')
threading.Thread(target=server.serve_forever, daemon=True).start()
asyncio.run(proxy.main())
