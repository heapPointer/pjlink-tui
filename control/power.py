import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pjlink_client import PJLinkClient

STATES = {'0': 'Standby', '1': 'On', '2': 'Cooling', '3': 'Warming'}


def get_power(host, password='', port=4352):
    client = PJLinkClient(host, password, port)
    resp = client.query('POWR')
    val = PJLinkClient.extract(resp, 'POWR')
    return val, STATES.get(val, val)


def set_power(host, state, password='', port=4352):
    client = PJLinkClient(host, password, port)
    resp = client.command('POWR', str(state))
    return PJLinkClient.extract(resp, 'POWR')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <host> [on|off|query] [password] [port]')
        sys.exit(1)

    host = sys.argv[1]
    action = sys.argv[2].lower() if len(sys.argv) > 2 else 'query'
    password = sys.argv[3] if len(sys.argv) > 3 else ''
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 4352

    if action == 'query':
        code, label = get_power(host, password, port)
        print(f'Power: {label} (code {code})')
    elif action in ('on', 'off'):
        result = set_power(host, 1 if action == 'on' else 0, password, port)
        print(f'Power {action}: {result}')
    else:
        print(f'Unknown action: {action}')
        sys.exit(1)
