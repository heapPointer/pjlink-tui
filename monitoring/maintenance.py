import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pjlink_client import PJLinkClient

LAMP_STATE = {'0': 'Off', '1': 'On'}


def parse_lamps(val):
    parts = val.split()
    lamps = []
    for i in range(0, len(parts) - 1, 2):
        try:
            lamps.append({
                'hours': int(parts[i]),
                'state': LAMP_STATE.get(parts[i + 1], parts[i + 1]),
            })
        except (ValueError, IndexError):
            pass
    return lamps


def get_maintenance(host, password='', port=4352):
    client = PJLinkClient(host, password, port)
    result = {}

    try:
        resp = client.query('LAMP')
        val = PJLinkClient.extract(resp, 'LAMP')
        result['lamps'] = parse_lamps(val)
    except Exception:
        pass

    for cmd, key in [('FILT', 'filter_hours'), ('RLMP', 'lamp_model'), ('RFIL', 'filter_model')]:
        try:
            resp = client.query(cmd, cls='2')
            val = PJLinkClient.extract(resp, cmd)
            result[key] = val
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

    print(f'[*] Maintenance data — {host}:{port}\n')
    info = get_maintenance(host, password, port)

    if not info:
        print('[-] No maintenance data retrieved')
        sys.exit(1)

    if 'lamps' in info:
        for i, lamp in enumerate(info['lamps'], 1):
            print(f'    Lamp {i}              {lamp["hours"]:,} hrs  [{lamp["state"]}]')

    if 'filter_hours' in info:
        print(f'    Filter              {info["filter_hours"]} hrs')

    if 'lamp_model' in info:
        print(f'    Lamp model          {info["lamp_model"]}')

    if 'filter_model' in info:
        print(f'    Filter model        {info["filter_model"]}')
