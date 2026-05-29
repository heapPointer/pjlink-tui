import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pjlink_client import PJLinkClient

FIELDS = ['Fan', 'Lamp', 'Temperature', 'Cover Open', 'Filter', 'Other']
LEVELS = {0: 'OK', 1: 'Warning', 2: 'Error'}


def get_error_status(host, password='', port=4352):
    client = PJLinkClient(host, password, port)
    resp = client.query('ERST')
    val = PJLinkClient.extract(resp, 'ERST')

    if len(val) < 6:
        return None

    return {
        field: {'code': int(val[i]), 'status': LEVELS.get(int(val[i]), f'Unknown({val[i]})')}
        for i, field in enumerate(FIELDS)
        if val[i].isdigit()
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <host> [password] [port]')
        sys.exit(1)

    host = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else ''
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 4352

    print(f'[*] Error status — {host}:{port}\n')
    errors = get_error_status(host, password, port)

    if errors is None:
        print('[-] Could not retrieve error status')
        sys.exit(1)

    any_issue = any(v['code'] > 0 for v in errors.values())
    for field, info in errors.items():
        marker = '[!]' if info['code'] > 0 else '[ ]'
        print(f'    {marker}  {field:<16}  {info["status"]}')

    print()
    if any_issue:
        print('[!] Faults detected')
    else:
        print('[+] All systems nominal')
