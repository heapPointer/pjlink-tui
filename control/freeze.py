import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pjlink_client import PJLinkClient

FREEZE_STATES = {'0': 'Unfrozen', '1': 'Frozen'}


def get_freeze(host, password='', port=4352):
    client = PJLinkClient(host, password, port)
    resp = client.query('FREZ', cls='2')
    val = PJLinkClient.extract(resp, 'FREZ')
    return val, FREEZE_STATES.get(val, val)


def set_freeze(host, frozen, password='', port=4352):
    client = PJLinkClient(host, password, port)
    resp = client.command('FREZ', '1' if frozen else '0', cls='2')
    return PJLinkClient.extract(resp, 'FREZ')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <host> [query|freeze|unfreeze] [password] [port]')
        sys.exit(1)

    host = sys.argv[1]
    action = sys.argv[2].lower() if len(sys.argv) > 2 else 'query'
    password = sys.argv[3] if len(sys.argv) > 3 else ''
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 4352

    if action == 'query':
        code, label = get_freeze(host, password, port)
        print(f'Freeze: {label}  (code {code})')
    elif action == 'freeze':
        result = set_freeze(host, True, password, port)
        print(f'Freeze applied: {result}')
    elif action == 'unfreeze':
        result = set_freeze(host, False, password, port)
        print(f'Freeze released: {result}')
    else:
        print(f'Unknown action: {action}')
        sys.exit(1)
