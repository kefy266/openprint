import socket
import subprocess
import concurrent.futures
from typing import List, Dict, Any

def scan_local_printers(subnet_prefix: str = "192.168.0") -> List[Dict[str, Any]]:
    """Scan local subnet for network printers with open IPP/RAW ports (631, 9100)."""
    discovered = []

    def probe_ip(ip: str):
        # Quick port 631 / 9100 check
        for port in [631, 9100]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.4)
                if s.connect_ex((ip, port)) == 0:
                    s.close()
                    return ip, port
                s.close()
            except:
                pass
        return None, None

    ips = [f"{subnet_prefix}.{i}" for i in range(1, 255)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
        results = list(ex.map(probe_ip, ips))

    for ip, port in results:
        if ip:
            discovered.append({
                "ip": ip,
                "port": port,
                "type": "IPP Network Printer" if port == 631 else "RAW JetDirect Printer",
                "uri": f"ipp://{ip}:631/ipp/print" if port == 631 else f"socket://{ip}:9100"
            })

    return discovered
