import platform
import socket
import psutil
import wmi


def get_ip():
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception:
        return None


def get_total_ram_gb():
    try:
        total_bytes = psutil.virtual_memory().total
        return round(total_bytes / (1024 ** 3), 2)
    except Exception:
        return None


def get_system_info():
    c = wmi.WMI()

    serial = None
    cpu = None

    try:
        bios = c.Win32_BIOS()[0]
        serial = bios.SerialNumber.strip()
    except Exception:
        pass

    try:
        processor = c.Win32_Processor()[0]
        cpu = processor.Name.strip()
    except Exception:
        pass

    return {
        "hostname": socket.gethostname(),
        "usuario": psutil.users()[0].name if psutil.users() else None,
        "cpu": cpu,
        "ram": f"{get_total_ram_gb()} GB" if get_total_ram_gb() else None,
        "sistema": f"{platform.system()} {platform.release()}",
        "ip": get_ip(),
        "serial": serial,
    }