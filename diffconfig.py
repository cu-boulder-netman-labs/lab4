import napalm
from tools import sshInfo, validateIP, connectivity
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import difflib
import os
from pathlib import Path

def compare_configs(device):
    host = device['host']

    # Validate IP
    if not validateIP.validate_ip(host):
        return host, "invalid ip"

    # Reachability check
    reachable = connectivity.check_reachability([host])
    if not reachable[host]:
        return host, "unreachable"

    try:
        driver = napalm.get_network_driver('ios')
        with driver(
            hostname=host,
            username=device['username'],
            password=device['password'],
        ) as dev:
            running_cfg = dev.get_config()['running']
            hostname = dev.get_facts()['hostname']

            dir_path = Path("configs")
            latest_file = max(dir_path.glob(f"{hostname}_*.txt"), key=os.path.getmtime)

            stored_cfg = latest_file.read_text()

            # Convert to line lists
            running_lines = running_cfg.splitlines(keepends=True)
            stored_lines = stored_cfg.splitlines(keepends=True)

            diff = difflib.unified_diff(
                stored_lines,
                running_lines,
                fromfile=f"{latest_file}",
                tofile=f"{hostname}_running"
            )

            diff_text = "".join(diff)

        return hostname, diff_text if diff_text else "no changes"

    except Exception as e:
        return f"{host} error: {e}"

def diff_config():
    hosts = sshInfo.load_ssh_info("config/sshInfo.json")

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(compare_configs, hosts)

    return results


if __name__ == "__main__":
    diff_config()