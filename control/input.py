import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pjlink_client import PJLinkClient

INPUT_TYPES = {
    '1': 'RGB', '2': 'Video', '3': 'Digital',
    '4': 'Storage', '5': 'Network', '6': 'Internal',
}


def decode(code):
    if len(code) >= 2:
        return f'{INPUT_TYPES.get(code[0], f"Type{code[0]}")}-{code[1]}'
    return code


def get_input(host, password='', port=4352):
    client = PJLinkClient(host, password, port)
    resp = client.query('INPT')
    val = PJLinkClient.extract(resp, 'INPT')
    return val, decode(val)


def set_input(host, input_code, password='', port=4352):
    client = PJLinkClient(host, password, port)
    resp = client.command('INPT', str(input_code))
    return PJLinkClient.extract(resp, 'INPT')


def list_inputs(host, password='', port=4352):
    client = PJLinkClient(host, password, port)
    resp = client.query('INST')
    val = PJLinkClient.extract(resp, 'INST')
    return [(c, decode(c)) for c in val.split()]


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <host> [query|list|<code>] [password] [port]')
        print('  Codes: 11=RGB-1  21=Video-1  31=Digital-1  51=Network-1')
        sys.exit(1)

    host = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else 'query'
    password = sys.argv[3] if len(sys.argv) > 3 else ''
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 4352

    if action == 'query':
        code, label = get_input(host, password, port)
        print(f'Current input: {code}  ({label})')
    elif action == 'list':
        inputs = list_inputs(host, password, port)
        print('Available inputs:')
        for code, label in inputs:
            print(f'  {code}  {label}')
    else:
        result = set_input(host, action, password, port)
        print(f'Switch to {action}: {result}')
