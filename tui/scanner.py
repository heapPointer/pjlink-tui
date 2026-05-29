import asyncio
import ipaddress
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pjlink_client import PJLinkClient, PJLinkError


@dataclass
class Host:
    ip: str
    auth_required: bool
    password: str = ''
    name: str = ''
    pjlink_class: str = ''
    caps: dict = field(default_factory=dict)


def _refresh_host_details(host: Host) -> None:
    c = PJLinkClient(host.ip, host.password)
    caps = {}

    try:
        host.name = PJLinkClient.extract(c.query('NAME'), 'NAME')
    except Exception:
        pass

    for cmd, key in [('POWR', 'power'), ('INPT', 'input'), ('AVMT', 'mute'), ('ERST', 'error_status')]:
        try:
            PJLinkClient.extract(c.query(cmd), cmd)
            caps[key] = True
        except PJLinkError as e:
            if e.code in ('ERR3', 'ERR4'):
                caps[key] = True
        except Exception:
            pass

    try:
        PJLinkClient.extract(c.query('LAMP'), 'LAMP')
        caps['lamp'] = True
    except PJLinkError as e:
        if e.code in ('ERR3', 'ERR4'):
            caps['lamp'] = True
    except Exception:
        pass

    try:
        host.pjlink_class = PJLinkClient.extract(c.query('CLSS'), 'CLSS')
    except Exception:
        pass

    if host.pjlink_class == '2':
        for cmd, key in [('FREZ', 'freeze'), ('SVOL', 'volume'), ('FILT', 'maintenance'), ('SNUM', 'serial')]:
            try:
                PJLinkClient.extract(c.query(cmd, cls='2'), cmd)
                caps[key] = True
            except PJLinkError as e:
                if e.code in ('ERR3', 'ERR4'):
                    caps[key] = True
            except Exception:
                pass

    host.caps = caps


def detect_caps_for_host(host: Host) -> None:
    _refresh_host_details(host)


async def _probe(ip: str, sem: asyncio.Semaphore, on_found, on_progress) -> None:
    async with sem:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, 4352), timeout=0.5
            )
            try:
                data = await asyncio.wait_for(reader.readuntil(b'\r'), timeout=0.5)
                banner = data.decode('ascii', errors='ignore').strip()
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass

            host = Host(ip=ip, auth_required=not banner.startswith('PJLINK 0'))
            on_found(host)

            if not host.auth_required:
                async def _enrich(h: Host = host) -> None:
                    try:
                        await asyncio.to_thread(_refresh_host_details, h)
                    except Exception:
                        pass
                    on_found(h)
                asyncio.create_task(_enrich())
        except Exception:
            pass
        finally:
            on_progress()


async def scan_cidr(cidr: str, on_found, on_progress, max_workers: int = 512) -> None:
    network = ipaddress.ip_network(cidr, strict=False)
    sem = asyncio.Semaphore(max_workers)
    tasks = [
        asyncio.create_task(_probe(str(ip), sem, on_found, on_progress))
        for ip in network.hosts()
    ]
    await asyncio.gather(*tasks)


def host_total(cidr: str) -> int:
    try:
        return sum(1 for _ in ipaddress.ip_network(cidr, strict=False).hosts())
    except ValueError:
        return 0
