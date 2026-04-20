import platform
import socket
from datetime import datetime

import psutil
import wmi


def get_ip():
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception:
        return None


def get_mac_address():
    try:
        interfaces = psutil.net_if_addrs()
        for interface_name, addresses in interfaces.items():
            for address in addresses:
                if getattr(address, "family", None) == psutil.AF_LINK:
                    return address.address
        return None
    except Exception:
        return None


def get_total_ram_gb():
    try:
        total_bytes = psutil.virtual_memory().total
        return round(total_bytes / (1024 ** 3), 2)
    except Exception:
        return None


def get_disk_info():
    try:
        disk = psutil.disk_usage("C:\\")
        total_gb = round(disk.total / (1024 ** 3), 2)
        free_gb = round(disk.free / (1024 ** 3), 2)
        return str(total_gb), str(free_gb)
    except Exception:
        return None, None


def get_last_boot():
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        return boot_time.isoformat()
    except Exception:
        return None


def get_system_info():
    c = wmi.WMI()

    serial = None
    cpu = None
    fabricante = None
    modelo = None
    motherboard = None
    bios_version = None
    versao_windows = None

    try:
        bios = c.Win32_BIOS()[0]
        serial = bios.SerialNumber.strip()
        bios_version = bios.SMBIOSBIOSVersion.strip()
    except Exception:
        pass

    try:
        processor = c.Win32_Processor()[0]
        cpu = processor.Name.strip()
    except Exception:
        pass

    try:
        system = c.Win32_ComputerSystem()[0]
        fabricante = system.Manufacturer.strip()
        modelo = system.Model.strip()
    except Exception:
        pass

    try:
        board = c.Win32_BaseBoard()[0]
        motherboard = f"{board.Manufacturer.strip()} {board.Product.strip()}"
    except Exception:
        pass

    try:
        os_info = c.Win32_OperatingSystem()[0]
        versao_windows = f"{os_info.Caption.strip()} {os_info.Version.strip()}"
    except Exception:
        pass

    disco_total_gb, disco_livre_gb = get_disk_info()

    return {
        "hostname": socket.gethostname(),
        "usuario": psutil.users()[0].name if psutil.users() else None,
        "cpu": cpu,
        "ram": f"{get_total_ram_gb()} GB" if get_total_ram_gb() else None,
        "sistema": f"{platform.system()} {platform.release()}",
        "ip": get_ip(),
        "serial": serial,
        "fabricante": fabricante,
        "modelo": modelo,
        "motherboard": motherboard,
        "bios_version": bios_version,
        "arquitetura": platform.machine(),
        "versao_windows": versao_windows,
        "mac_address": get_mac_address(),
        "disco_total_gb": disco_total_gb,
        "disco_livre_gb": disco_livre_gb,
        "ultimo_boot": get_last_boot(),
    }