import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pjlink_client import PJLinkClient

MUTE_TYPE = {'1': 'Video', '2': 'Audio', '3': 'Video+Audio'}
MUTE_STATE = {'0': 'Unmuted', '1': 'Muted'}

ACTIONS = {
    'video-on':  ('1', '1'),
    'video-off': ('1', '0'),
    'audio-on':  ('2', '1'),
    'audio-off': ('2', '0'),
    'all-on':    ('3', '1'),
    'all-off':   ('3', '0'),
}


def get_mute(host, password='', port=4352):
    client = PJLinkClient(host, password, port)
    resp = client.query('AVMT')
    val = PJLinkClient.extract(resp, 'AVMT')
    if len(val) == 2:
        return val, f'{MUTE_TYPE.get(val[0], val[0])}: {MUTE_STATE.get(val[1], val[1])}'
    return val, val


def set_mute(host, mtype, state, password='', port=4352):
    client = PJLinkClient(host, password, port)
    resp = client.command('AVMT', f'{mtype}{state}')
    return PJLinkClient.extract(resp, 'AVMT')


if __name__ == '__main__':
    valid = '  '.join(ACTIONS.keys())
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <host> [query|{valid}] [password] [port]')
        sys.exit(1)

    host = sys.argv[1]
    action = sys.argv[2].lower() if len(sys.argv) > 2 else 'query'
    password = sys.argv[3] if len(sys.argv) > 3 else ''
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 4352

    if action == 'query':
        code, label = get_mute(host, password, port)
        print(f'Mute state: {label}  (code {code})')
    elif action in ACTIONS:
        mtype, state = ACTIONS[action]
        result = set_mute(host, mtype, state, password, port)
        print(f'Mute {action}: {result}')
    else:
        print(f'Unknown action: {action}')
        sys.exit(1)
