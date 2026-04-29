import socket
from collections import namedtuple
from types import SimpleNamespace

from agent import collector

Address = namedtuple("Address", ["family", "address"])


def test_select_primary_network_interface_prefers_physical_with_ip():
    interfaces = [
        {
            "name": "VPN Adapter",
            "mac_address": "AA-BB-CC-00-00-01",
            "ip_addresses": ["10.8.0.2"],
            "is_virtual": True,
        },
        {
            "name": "Ethernet",
            "mac_address": "AA-BB-CC-00-00-02",
            "ip_addresses": ["192.168.0.10"],
            "is_virtual": False,
        },
    ]

    primary = collector.select_primary_network_interface(interfaces)

    assert primary["name"] == "Ethernet"
    assert primary["mac_address"] == "AA-BB-CC-00-00-02"


def test_get_network_interfaces_filters_down_and_normalizes(monkeypatch):
    monkeypatch.setattr(
        collector.psutil,
        "net_if_addrs",
        lambda: {
            "Ethernet": [
                Address(collector.psutil.AF_LINK, "aa:bb:cc:00:00:02"),
                Address(socket.AF_INET, "192.168.0.10"),
            ],
            "Loopback": [
                Address(collector.psutil.AF_LINK, "00:00:00:00:00:00"),
                Address(socket.AF_INET, "127.0.0.1"),
            ],
            "Disconnected": [
                Address(collector.psutil.AF_LINK, "aa:bb:cc:00:00:03"),
                Address(socket.AF_INET, "192.168.0.11"),
            ],
        },
    )
    monkeypatch.setattr(
        collector.psutil,
        "net_if_stats",
        lambda: {
            "Ethernet": SimpleNamespace(isup=True),
            "Loopback": SimpleNamespace(isup=True),
            "Disconnected": SimpleNamespace(isup=False),
        },
    )

    interfaces = collector.get_network_interfaces()

    assert interfaces == [
        {
            "name": "Ethernet",
            "mac_address": "AA-BB-CC-00-00-02",
            "ip_addresses": ["192.168.0.10"],
            "is_virtual": False,
        }
    ]


def test_get_system_info_works_without_wmi(monkeypatch):
    monkeypatch.setattr(collector, "wmi", None)
    monkeypatch.setattr(collector.socket, "gethostname", lambda: "PC-TEST")
    monkeypatch.setattr(collector, "get_network_interfaces", lambda: [])
    monkeypatch.setattr(collector, "get_disk_info", lambda: ("100.0", "50.0"))
    monkeypatch.setattr(collector, "get_total_ram_gb", lambda: 8.0)
    monkeypatch.setattr(collector, "get_last_boot", lambda: "2026-04-29T10:00:00")
    monkeypatch.setattr(collector.psutil, "users", lambda: [])

    data = collector.get_system_info()

    assert data["hostname"] == "PC-TEST"
    assert data["serial"] is None
    assert data["ip"] is None
    assert data["mac_address"] is None
    assert data["network_interfaces"] == []
