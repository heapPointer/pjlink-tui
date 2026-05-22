import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pjlink_client import PJLinkClient

INPUT_TYPES = {
    '1': 'RGB', '2': 'Video', '3': 'Digital',
    '4': 'Storage', '5': 'Network', '6': 'Internal',
}


def decode_input(code):
    if len(code) >= 2:
        label = INPUT_TYPES.get(code[0], f'Type{code[0]}')
        return f'{label}-{code[1]}'
    return code


def get_input_info(host, password='', port=4352):
    client = PJLinkClient(host, password, port)
    result = {}

    try:
        resp = client.query('INPT', cls='1')
        val = PJLinkClient.extract(resp, 'INPT')
        result['current_input'] = val
        result['current_input_label'] = decode_input(val)
    except Exception:
        pass

    try:
        resp = client.query('INST', cls='1')
        val = PJLinkClient.extract(resp, 'INST')
        inputs = val.split()
        result['available'] = inputs
        result['available_labels'] = {i: decode_input(i) for i in inputs}
    except Exception:
        pass

    if 'available' in result:
        names = {}
        for inp in result['available']:
            try:
                resp = client.command('INNM', inp, cls='2')
                val = PJLinkClient.extract(resp, 'INNM')
                names[inp] = val
            except Exception:
                pass
        if names:
            result['input_names'] = names

    try:
        resp = client.query('IRES', cls='2')
        val = PJLinkClient.extract(resp, 'IRES')
        result['signal_resolution'] = val
    except Exception:
        pass

    try:
        resp = client.query('RRES', cls='2')
        val = PJLinkClient.extract(resp, 'RRES')
        result['recommended_resolution'] = val
    except Exception:
        pass

    return result


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <host> [password] [port]')
        sys.exit(1)

    host = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else ''
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 4352

    print(f'[*] Enumerating inputs on Epson projector at {host}:{port}\n')
    info = get_input_info(host, password, port)

    if not info:
        print('[-] No input information retrieved')
        sys.exit(1)

    if 'current_input' in info:
        print(f'    Current input  : {info["current_input"]}  ({info.get("current_input_label", "")})')

    if 'available' in info:
        print(f'\n    Available inputs:')
        for code in info['available']:
            label = info['available_labels'].get(code, '')
            name = info.get('input_names', {}).get(code, '')
            suffix = f'  "{name}"' if name else ''
            print(f'      {code}  {label}{suffix}')

    if 'signal_resolution' in info:
        print(f'\n    Signal resolution      : {info["signal_resolution"]}')
    if 'recommended_resolution' in info:
        print(f'    Recommended resolution : {info["recommended_resolution"]}')
