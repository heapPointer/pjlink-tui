import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pjlink_client import PJLinkClient

FIELDS = [
    ('CLSS', '1', 'PJLink Class'),
    ('NAME', '1', 'Projector Name'),
    ('INF1', '1', 'Manufacturer'),
    ('INF2', '1', 'Product Name'),
    ('INFO', '1', 'Other Info'),
    ('SNUM', '2', 'Serial Number'),
    ('SVER', '2', 'Software Version'),
]


def get_device_info(host, password='', port=4352):
    client = PJLinkClient(host, password, port)
    info = {}

    for cmd, cls, label in FIELDS:
        try:
            resp = client.query(cmd, cls=cls)
            val = PJLinkClient.extract(resp, cmd)
            info[label] = val
        except Exception:
            pass

    return info


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <host> [password] [port]')
        sys.exit(1)

    host = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else ''
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 4352

    print(f'[*] Fingerprinting Epson projector at {host}:{port}\n')
    info = get_device_info(host, password, port)

    if not info:
        print('[-] No device information retrieved')
        sys.exit(1)

    for label, value in info.items():
        print(f'    {label:<22} {value}')
