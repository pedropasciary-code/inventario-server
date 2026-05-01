import platform
import socket
from datetime import datetime
import ipaddress

import psutil

try:
    import wmi
except ImportError:
    wmi = None

VIRTUAL_INTERFACE_KEYWORDS = [
    "bluetooth",
    "docker",
    "hyper-v",
    "isatap",
    "loopback",
    "teredo",
    "virtual",
    "vmware",
    "vpn",
    "vbox",
    "virtualbox",
    "wi-fi direct",
    "wireguard",
    "wsl",
]


def normalize_mac_address(mac_address):
    if not mac_address:
        return None

    mac_address = mac_address.strip().upper().replace(":", "-")

    if mac_address in {"00-00-00-00-00-00", "FF-FF-FF-FF-FF-FF"}:
        return None

    return mac_address or None


def is_virtual_interface(interface_name):
    interface_name = interface_name.lower()
    return any(keyword in interface_name for keyword in VIRTUAL_INTERFACE_KEYWORDS)


def is_usable_ip(ip_address):
    try:
        ip = ipaddress.ip_address(ip_address)
        return not (
            ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_unspecified
        )
    except Exception:
        return False


def get_network_interfaces():
    interfaces = []

    try:
        addresses_by_interface = psutil.net_if_addrs()
        stats_by_interface = psutil.net_if_stats()

        for interface_name, addresses in addresses_by_interface.items():
            stats = stats_by_interface.get(interface_name)

            if stats and not stats.isup:
                continue

            mac_address = None
            ip_addresses = []

            for address in addresses:
                family = getattr(address, "family", None)

                if family == psutil.AF_LINK:
                    mac_address = normalize_mac_address(address.address)
                elif family in {socket.AF_INET, socket.AF_INET6} and is_usable_ip(address.address):
                    ip_addresses.append(address.address)

            if not mac_address and not ip_addresses:
                continue

            interfaces.append(
                {
                    "name": interface_name,
                    "mac_address": mac_address,
                    "ip_addresses": ip_addresses,
                    "is_virtual": is_virtual_interface(interface_name),
                }
            )
    except Exception:
        return []

    return interfaces


def select_primary_network_interface(interfaces):
    physical_interfaces = [
        interface
        for interface in interfaces
        if not interface["is_virtual"] and interface["mac_address"]
    ]

    interfaces_with_ip = [
        interface
        for interface in physical_interfaces
        if interface["ip_addresses"]
    ]

    if interfaces_with_ip:
        return interfaces_with_ip[0]

    if physical_interfaces:
        return physical_interfaces[0]

    for interface in interfaces:
        if interface["mac_address"]:
            return interface

    return interfaces[0] if interfaces else None


def get_ip():
    primary_interface = select_primary_network_interface(get_network_interfaces())

    if primary_interface and primary_interface["ip_addresses"]:
        return primary_interface["ip_addresses"][0]

    return None


def get_mac_address():
    primary_interface = select_primary_network_interface(get_network_interfaces())

    if primary_interface:
        return primary_interface["mac_address"]

    return None


def get_total_ram_gb():
    try:
        # Converte a memória total de bytes para gigabytes com duas casas decimais.
        total_bytes = psutil.virtual_memory().total
        return round(total_bytes / (1024 ** 3), 2)
    except Exception:
        return None


def get_disk_info():
    try:
        # Lê o uso da unidade C: para reportar espaço total e livre no inventário.
        disk = psutil.disk_usage("C:\\")
        total_gb = round(disk.total / (1024 ** 3), 2)
        free_gb = round(disk.free / (1024 ** 3), 2)
        return str(total_gb), str(free_gb)
    except Exception:
        return None, None


def get_last_boot():
    try:
        # Retorna a data do último boot em ISO para facilitar o parse na API.
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        return boot_time.isoformat()
    except Exception:
        return None


def get_system_info():
    # Inicializa a interface WMI para consultar detalhes mais profundos do Windows.
    c = wmi.WMI() if wmi else None

    serial = None
    cpu = None
    fabricante = None
    modelo = None
    motherboard = None
    bios_version = None
    versao_windows = None

    try:
        # BIOS fornece serial da máquina e versão do firmware.
        bios = c.Win32_BIOS()[0] if c else None
        if not bios:
            raise RuntimeError("WMI indisponível")
        serial = bios.SerialNumber.strip()
        bios_version = bios.SMBIOSBIOSVersion.strip()
    except Exception:
        pass

    try:
        # Recupera o nome comercial do processador instalado.
        processor = c.Win32_Processor()[0] if c else None
        if not processor:
            raise RuntimeError("WMI indisponível")
        cpu = processor.Name.strip()
    except Exception:
        pass

    try:
        # Obtém fabricante e modelo reportados pelo sistema.
        system = c.Win32_ComputerSystem()[0] if c else None
        if not system:
            raise RuntimeError("WMI indisponível")
        fabricante = system.Manufacturer.strip()
        modelo = system.Model.strip()
    except Exception:
        pass

    try:
        # Identifica a placa-mãe combinando fabricante e produto.
        board = c.Win32_BaseBoard()[0] if c else None
        if not board:
            raise RuntimeError("WMI indisponível")
        motherboard = f"{board.Manufacturer.strip()} {board.Product.strip()}"
    except Exception:
        pass

    try:
        # Monta uma descrição amigável da versão do Windows instalada.
        os_info = c.Win32_OperatingSystem()[0] if c else None
        if not os_info:
            raise RuntimeError("WMI indisponível")
        versao_windows = f"{os_info.Caption.strip()} {os_info.Version.strip()}"
    except Exception:
        pass

    # Completa a coleta com métricas gerais vindas do psutil.
    disco_total_gb, disco_livre_gb = get_disk_info()
    total_ram_gb = get_total_ram_gb()
    network_interfaces = get_network_interfaces()
    primary_network_interface = select_primary_network_interface(network_interfaces)

    # Consolida todos os campos em um payload compatível com o schema da API.
    return {
        "hostname": socket.gethostname(),
        "usuario": psutil.users()[0].name if psutil.users() else None,
        "cpu": cpu,
        "ram": f"{total_ram_gb} GB" if total_ram_gb else None,
        "sistema": f"{platform.system()} {platform.release()}",
        "ip": primary_network_interface["ip_addresses"][0] if primary_network_interface and primary_network_interface["ip_addresses"] else None,
        "serial": serial,
        "fabricante": fabricante,
        "modelo": modelo,
        "motherboard": motherboard,
        "bios_version": bios_version,
        "arquitetura": platform.machine(),
        "versao_windows": versao_windows,
        "mac_address": primary_network_interface["mac_address"] if primary_network_interface else None,
        "network_interfaces": network_interfaces,
        "disco_total_gb": disco_total_gb,
        "disco_livre_gb": disco_livre_gb,
        "ultimo_boot": get_last_boot(),
    }
