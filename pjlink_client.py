import socket
import hashlib


class PJLinkError(Exception):
    def __init__(self, msg='', code=''):
        super().__init__(msg)
        self.code = code


class AuthError(PJLinkError):
    pass


class PJLinkClient:
    def __init__(self, host, password='', port=4352, timeout=5):
        self.host = host
        self.password = password
        self.port = port
        self.timeout = timeout

    def _recv_line(self, sock):
        buf = b''
        while not buf.endswith(b'\r'):
            chunk = sock.recv(512)
            if not chunk:
                break
            buf += chunk
        return buf.decode('ascii').strip()

    def _open_session(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        banner = self._recv_line(sock)

        if 'ERRA' in banner:
            sock.close()
            raise AuthError(f'Device rejected connection: {banner}')

        prefix = ''
        if banner.startswith('PJLINK 1'):
            parts = banner.split()
            nonce = parts[2] if len(parts) > 2 else ''
            prefix = hashlib.md5((nonce + self.password).encode('ascii')).hexdigest()
        elif not banner.startswith('PJLINK 0'):
            sock.close()
            raise PJLinkError(f'Unexpected banner: {banner}')

        return sock, prefix

    def send(self, command):
        sock, prefix = self._open_session()
        try:
            sock.sendall((prefix + command + '\r').encode('ascii'))
            return self._recv_line(sock)
        finally:
            sock.close()

    def query(self, cmd, cls='1'):
        return self.send(f'%{cls}{cmd} ?')

    def command(self, cmd, param, cls='1'):
        return self.send(f'%{cls}{cmd} {param}')

    @staticmethod
    def extract(response, cmd):
        for cls in ('1', '2'):
            prefix = f'%{cls}{cmd}='
            if response.startswith(prefix):
                val = response[len(prefix):]
                if val == 'ERRA':
                    raise AuthError('Authentication failure')
                if val.startswith('ERR'):
                    raise PJLinkError(f'Command error: {val}', code=val)
                return val
        if 'ERRA' in response:
            raise AuthError('Authentication failure')
        if 'ERR' in response:
            raise PJLinkError(f'Command error: {response}')
        return response
