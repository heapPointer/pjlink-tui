import asyncio
import os
import sys
from dataclasses import dataclass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TUI  = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(_ROOT, 'monitoring'))
sys.path.insert(0, os.path.join(_ROOT, 'enum'))
sys.path.insert(0, os.path.join(_ROOT, 'control'))
sys.path.insert(0, _TUI)
sys.path.insert(0, _ROOT)

from scanner import Host

from power import set_power
from freeze import set_freeze
from mute import set_mute
from input import set_input
from volume import set_volume
from device_info import get_device_info
from input_info import get_input_info
from error_status import get_error_status
from maintenance import get_maintenance


@dataclass
class Action:
    id: str
    label: str
    requires_cap: str | None = None
    needs_param: str | None = None


CATALOGUE: list[Action] = [
    Action('power_on',     'Power On',           'power'),
    Action('power_off',    'Power Off',           'power'),
    Action('freeze',       'Freeze Image',        'freeze'),
    Action('unfreeze',     'Unfreeze Image',      'freeze'),
    Action('mute_all',     'Mute (Video+Audio)',  'mute'),
    Action('unmute_all',   'Unmute',              'mute'),
    Action('switch_input', 'Switch Input',        'input',  'Input code (e.g. 31 = HDMI-1)'),
    Action('device_info',  'Get Device Info',     None),
    Action('error_status', 'Error Status',        'error_status'),
    Action('lamp_status',  'Lamp Status',         'lamp'),
    Action('maintenance',  'Maintenance Report',  'maintenance'),
    Action('speaker_vol',  'Speaker Volume',      'volume', 'Level (0–255)'),
    Action('mic_vol',      'Mic Volume',          'volume', 'Level (0–255)'),
    Action('input_list',   'Input List',          'input'),
]


def available_actions(host: Host) -> list[Action]:
    return [a for a in CATALOGUE if a.requires_cap is None or host.caps.get(a.requires_cap)]


def _fmt_dict(d: dict) -> str:
    if not d:
        return '(no data)'
    return '  |  '.join(f'{k}: {v}' for k, v in d.items())


def _fmt_errors(errors) -> str:
    if errors is None:
        return '(unavailable)'
    issues = [f'{k}: {v["status"]}' for k, v in errors.items() if v['code'] > 0]
    return ', '.join(issues) if issues else 'All systems nominal'


def _fmt_maintenance(info: dict) -> str:
    parts = []
    for i, lamp in enumerate(info.get('lamps', []), 1):
        parts.append(f'Lamp{i}: {lamp["hours"]}h [{lamp["state"]}]')
    if 'filter_hours' in info:
        parts.append(f'Filter: {info["filter_hours"]}h')
    if 'lamp_model' in info:
        parts.append(f'LampModel: {info["lamp_model"]}')
    if 'filter_model' in info:
        parts.append(f'FilterModel: {info["filter_model"]}')
    return '  |  '.join(parts) if parts else '(no data)'


def _fmt_inputs(info: dict) -> str:
    if 'available' not in info:
        return '(no data)'
    parts = []
    for code in info['available']:
        label = info.get('available_labels', {}).get(code, '')
        name = info.get('input_names', {}).get(code, '')
        entry = f'{code}={label}'
        if name:
            entry += f'({name})'
        parts.append(entry)
    current = info.get('current_input', '')
    result = '  '.join(parts)
    if current:
        result = f'Current:{current}  >>  ' + result
    return result


def _run_action(action_id: str, host: Host, param: str) -> str:
    h, pw = host.ip, host.password

    match action_id:
        case 'power_on':
            return str(set_power(h, 1, pw))
        case 'power_off':
            return str(set_power(h, 0, pw))
        case 'freeze':
            return str(set_freeze(h, True, pw))
        case 'unfreeze':
            return str(set_freeze(h, False, pw))
        case 'mute_all':
            return str(set_mute(h, 3, True, pw))
        case 'unmute_all':
            return str(set_mute(h, 3, False, pw))
        case 'switch_input':
            return str(set_input(h, param.strip(), pw))
        case 'device_info':
            return _fmt_dict(get_device_info(h, pw))
        case 'error_status':
            return _fmt_errors(get_error_status(h, pw))
        case 'lamp_status' | 'maintenance':
            return _fmt_maintenance(get_maintenance(h, pw))
        case 'speaker_vol':
            return str(set_volume(h, 'SVOL', param.strip(), pw))
        case 'mic_vol':
            return str(set_volume(h, 'MVOL', param.strip(), pw))
        case 'input_list':
            return _fmt_inputs(get_input_info(h, pw))
        case _:
            return f'Unknown action: {action_id}'


async def execute(action_id: str, host: Host, param: str = '') -> str:
    return await asyncio.to_thread(_run_action, action_id, host, param)
