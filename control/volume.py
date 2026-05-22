import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pjlink_client import PJLinkClient


def get_volume(host, password='', port=4352):
    client = PJLinkClient(host, password, port)
    result = {}

    for cmd, key in [('SVOL', 'speaker'), ('MVOL', 'mic')]:
        try:
            resp = client.query(cmd, cls='2')
            val = PJLinkClient.extract(resp, cmd)
            result[key] = val
        except Exception:
            result[key] = None

    return result


def set_volume(host, cmd, level, password='', port=4352):
    client = PJLinkClient(host, password, port)
    level = max(0, min(255, int(level)))
    resp = client.command(cmd, str(level), cls='2')
    return PJLinkClient.extract(resp, cmd)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <host> [query|speaker <0-255>|mic <0-255>] [password] [port]')
        sys.exit(1)

    host = sys.argv[1]
    action = sys.argv[2].lower() if len(sys.argv) > 2 else 'query'

    if action in ('speaker', 'mic'):
        if len(sys.argv) < 4:
            print('Error: volume level required')
            sys.exit(1)
        level = sys.argv[3]
        password = sys.argv[4] if len(sys.argv) > 4 else ''
        port = int(sys.argv[5]) if len(sys.argv) > 5 else 4352
        cmd = 'SVOL' if action == 'speaker' else 'MVOL'
        result = set_volume(host, cmd, level, password, port)
        print(f'{action.capitalize()} volume -> {result}')
    else:
        password = sys.argv[3] if len(sys.argv) > 3 else ''
        port = int(sys.argv[4]) if len(sys.argv) > 4 else 4352
        vol = get_volume(host, password, port)
        spk = vol['speaker'] if vol['speaker'] is not None else 'not supported'
        mic = vol['mic'] if vol['mic'] is not None else 'not supported'
        print(f'Speaker : {spk}')
        print(f'Mic     : {mic}')
