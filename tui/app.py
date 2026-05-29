import asyncio
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TUI  = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
sys.path.insert(0, _TUI)

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    ProgressBar,
    RichLog,
)

from scanner import Host, detect_caps_for_host, host_total, scan_cidr
from actions import Action, CATALOGUE, available_actions, execute


_CAP_SHORT = {
    'power':        'pwr',
    'input':        'in',
    'mute':         'mute',
    'error_status': 'err',
    'lamp':         'lamp',
    'freeze':       'frz',
    'volume':       'vol',
    'maintenance':  'mnt',
    'serial':       'sn',
}


def _cap_summary(host: Host) -> str:
    return ' '.join(_CAP_SHORT[k] for k in _CAP_SHORT if host.caps.get(k))


class HostFound(Message):
    def __init__(self, host: Host) -> None:
        super().__init__()
        self.host = host


class ProgressTick(Message):
    pass


class ScanComplete(Message):
    pass


class PasswordModal(ModalScreen):

    DEFAULT_CSS = """
    PasswordModal {
        align: center middle;
    }
    PasswordModal > Vertical {
        width: 52;
        height: auto;
        border: thick $accent;
        padding: 2 4;
        background: $surface;
    }
    PasswordModal Label {
        margin-bottom: 1;
    }
    """

    def __init__(self, ip: str) -> None:
        super().__init__()
        self.ip = ip
        self._value: str = ''

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f'[bold]PJLink Password[/bold]')
            yield Label(f'[dim]{self.ip}[/dim]')
            yield Input(placeholder='password...', password=True, id='pw-input')
            yield Label('[dim]↵ confirm   Esc cancel[/dim]')

    async def on_mount(self) -> None:
        self.query_one('#pw-input', Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._value = event.value
        self.dismiss(self._value)

    def on_key(self, event) -> None:
        if event.key == 'escape':
            self.dismiss('')


class ParamModal(ModalScreen):

    DEFAULT_CSS = """
    ParamModal {
        align: center middle;
    }
    ParamModal > Vertical {
        width: 52;
        height: auto;
        border: thick $accent;
        padding: 2 4;
        background: $surface;
    }
    ParamModal Label {
        margin-bottom: 1;
    }
    """

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.prompt)
            yield Input(id='param-input')
            yield Label('[dim]↵ confirm   Esc cancel[/dim]')

    async def on_mount(self) -> None:
        self.query_one('#param-input', Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def on_key(self, event) -> None:
        if event.key == 'escape':
            self.dismiss(None)


class PJLinkScannerApp(App):

    CSS = """
    Screen {
        layout: vertical;
    }

    #scan-bar {
        height: 3;
        layout: horizontal;
        padding: 0 1;
        background: $panel;
    }

    #cidr-input {
        width: 38;
    }

    #scan-btn {
        width: 10;
        margin: 0 1;
    }

    #progress {
        width: 1fr;
        margin-top: 1;
        margin-right: 1;
    }

    #main-area {
        height: 1fr;
        layout: horizontal;
    }

    #hosts-panel {
        width: 44%;
        border: solid $accent;
        padding: 0 1;
    }

    #hosts-label {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }

    #search-input-panel {
        width: 1fr;
        margin: 0 1;
    }

    #actions-panel {
        width: 56%;
        border: solid $accent;
        padding: 0 1;
    }

    #actions-label {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }

    #output {
        height: 7;
        border: solid $surface-lighten-1;
    }
    """

    BINDINGS = [
        Binding('q', 'quit', 'Quit'),
        Binding('r', 'rescan', 'Rescan'),
        Binding('tab', 'focus_next', 'Next panel'),
        Binding('shift+tab', 'focus_previous', 'Prev panel'),
        Binding('f5', 'rescan', 'Rescan'),
    ]

    def __init__(self, cidr: str = '') -> None:
        super().__init__()
        self._cidr = cidr
        self._hosts: dict[str, Host] = {}
        self._selected_host: Host | None = None
        self._search_query = ''
        self._scanning = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id='scan-bar'):
            yield Input(
                value=self._cidr,
                placeholder='CIDR range  e.g. 10.113.164.0/24',
                id='cidr-input',
            )
            yield Button('Scan', id='scan-btn', variant='primary')
            yield ProgressBar(id='progress', show_eta=False)
        with Horizontal(id='main-area'):
            with Vertical(id='hosts-panel'):
                yield Label('Devices', id='hosts-label')
                yield Input(placeholder='Filter projector name or IP', id='search-input-panel')
                yield DataTable(id='hosts', cursor_type='row', zebra_stripes=True)
            with Vertical(id='actions-panel'):
                yield Label('Select a device', id='actions-label')
                yield ListView(id='actions')
        yield RichLog(id='output', highlight=True, markup=True, wrap=True)
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one('#hosts', DataTable)
        table.add_column('IP Address',    key='ip',   width=17)
        table.add_column('Name',          key='name', width=22)
        table.add_column('Auth',          key='auth', width=6)
        table.add_column('Cls',           key='cls',  width=4)
        table.add_column('Capabilities', key='caps')

        if self._cidr:
            await self._start_scan()

    async def _start_scan(self) -> None:
        cidr = self.query_one('#cidr-input', Input).value.strip()
        if not cidr or self._scanning:
            return

        total = host_total(cidr)
        if total == 0:
            self._log(f'[red]Invalid CIDR: {cidr}[/red]')
            return

        self._scanning = True
        self._hosts.clear()
        self._selected_host = None
        self._render_hosts()

        self.query_one('#actions-label', Label).update('Select a device')
        self.query_one('#actions', ListView).clear()

        pb = self.query_one('#progress', ProgressBar)
        pb.update(total=total, progress=0)

        self._log(f'[bold cyan]Scanning {cidr} — {total} hosts on TCP/4352[/bold cyan]')
        asyncio.create_task(self._run_scan(cidr))

    async def _run_scan(self, cidr: str) -> None:
        try:
            await scan_cidr(
                cidr,
                on_found=lambda h: self.post_message(HostFound(h)),
                on_progress=lambda: self.post_message(ProgressTick()),
            )
        finally:
            self._scanning = False
            self.post_message(ScanComplete())

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'scan-btn':
            await self._start_scan()

    def on_host_found(self, message: HostFound) -> None:
        host = message.host
        self._hosts[host.ip] = host
        self._render_hosts()

    def on_progress_tick(self, _: ProgressTick) -> None:
        self.query_one('#progress', ProgressBar).advance(1)

    def on_scan_complete(self, _: ScanComplete) -> None:
        count = len(self._hosts)
        self._log(f'[green]Scan complete — {count} PJLink device(s) found[/green]')

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None:
            return
        ip = str(event.row_key.value)
        host = self._hosts.get(ip)
        if not host:
            return
        self._selected_host = host
        self._populate_actions(host)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != 'search-input-panel':
            return
        self._search_query = event.value.strip()
        self._render_hosts()

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key is None:
            return
        ip = str(event.row_key.value)
        host = self._hosts.get(ip)
        if not host or not host.auth_required or host.password:
            return
        self.run_worker(
            self._unlock_host(host),
            name=f'unlock-{host.ip}',
            group='unlock',
            exclusive=True,
        )

    async def _unlock_host(self, host: Host) -> None:
        password = await self.push_screen_wait(PasswordModal(host.ip))
        if not password:
            return
        await self._apply_password_to_listed_hosts(password, host)

    async def _apply_password_to_listed_hosts(self, password: str, primary_host: Host) -> None:
        auth_hosts = sorted(
            (host for host in self._hosts.values() if host.auth_required),
            key=lambda item: (item.ip != primary_host.ip, item.ip),
        )

        for host in auth_hosts:
            host.password = password
            self._log(f'[yellow][>] {host.ip}  refreshing projector details...[/yellow]')
            try:
                await asyncio.to_thread(detect_caps_for_host, host)
                self._log(
                    f'[green][+] {host.ip}  authenticated — '
                    f'{len(host.caps)} capabilities  class {host.pjlink_class or "?"}[/green]'
                )
            except Exception as e:
                host.password = ''
                self._log(f'[red][-] {host.ip}  authentication failed: {e}[/red]')

            self._render_hosts()

        if primary_host.password:
            self._selected_host = primary_host
            self._populate_actions(primary_host)

    def _populate_actions(self, host: Host) -> None:
        lv = self.query_one('#actions', ListView)
        lv.clear()

        cls_tag = f'Class {host.pjlink_class}' if host.pjlink_class else 'Class ?'
        auth_tag = 'AUTH' if host.auth_required else 'OPEN'
        self.query_one('#actions-label', Label).update(
            f'{host.name or host.ip}  [{auth_tag}  {cls_tag}]'
        )

        if host.auth_required and not host.password:
            lv.append(ListItem(
                Label('[dim]Press Enter on this row to enter password[/dim]'),
                name='__locked__',
            ))
            return

        actions = available_actions(host)
        if not actions:
            lv.append(ListItem(
                Label('[dim](no capabilities detected)[/dim]'),
                name='__none__',
            ))
            return

        for action in actions:
            lv.append(ListItem(Label(action.label), name=action.id))

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        action_id = event.item.name
        if action_id in ('__locked__', '__none__') or self._selected_host is None:
            return

        action = next((a for a in CATALOGUE if a.id == action_id), None)
        if action is None:
            return

        host = self._selected_host
        self.run_worker(
            self._run_action_with_param(action, host),
            name=f'action-{host.ip}-{action.id}',
            group='action',
            exclusive=True,
        )

    async def _run_action_with_param(self, action: Action, host: Host) -> None:
        param = ''
        if action.needs_param:
            result = await self.push_screen_wait(ParamModal(action.needs_param))
            if not result:
                return
            param = result

        self._log(f'[yellow][>] {host.ip}  {action.label}...[/yellow]')
        try:
            output = await execute(action.id, host, param)
            self._log(f'[green][+] {host.ip}  {action.label}:  {output}[/green]')
        except Exception as e:
            self._log(f'[red][-] {host.ip}  {action.label} failed:  {e}[/red]')

    async def action_rescan(self) -> None:
        if not self._scanning:
            await self._start_scan()

    def _host_matches_query(self, host: Host) -> bool:
        query = self._search_query.casefold()
        if not query:
            return True
        return query in host.ip.casefold() or query in host.name.casefold()

    def _render_hosts(self) -> None:
        table = self.query_one('#hosts', DataTable)
        table.clear()

        visible_hosts = [host for host in sorted(self._hosts.values(), key=lambda item: item.ip) if self._host_matches_query(host)]
        for host in visible_hosts:
            auth_cell = '[red]AUTH[/red]' if host.auth_required else '[green]OPEN[/green]'
            table.add_row(
                host.ip,
                host.name or ('[dim](locked)[/dim]' if host.auth_required and not host.password else ''),
                auth_cell,
                host.pjlink_class or '?',
                _cap_summary(host),
                key=host.ip,
            )

        visible_count = len(visible_hosts)
        total_count = len(self._hosts)
        self.query_one('#hosts-label', Label).update(f'Devices  [{visible_count}/{total_count}]')

        if self._selected_host and self._host_matches_query(self._selected_host):
            self._populate_actions(self._selected_host)
        else:
            self._selected_host = None
            self.query_one('#actions-label', Label).update('Select a device')
            self.query_one('#actions', ListView).clear()

    def _log(self, msg: str) -> None:
        self.query_one('#output', RichLog).write(msg)


if __name__ == '__main__':
    cidr_arg = sys.argv[1] if len(sys.argv) > 1 else ''
    PJLinkScannerApp(cidr_arg).run()
