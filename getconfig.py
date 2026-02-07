import napalm
from tools import sshInfo, validateIP, connectivity
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

def process_config(device):
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
            cfg = dev.get_config()

            # Save in a file based on hostname and ISO8601 format
            hostname = dev.get_facts()['hostname']
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            fname = f"configs/{hostname}_{ts}.cfg"

            with open(fname, "w") as f:
                f.write(cfg["running"])

        return fname

    except Exception as e:
        return f"{host} error: {e}"

def get_config():
    hosts = sshInfo.load_ssh_info("config/sshInfo.json")

    with ThreadPoolExecutor(max_workers=10) as executor:
        files = executor.map(process_config, hosts)

    return list(files)


if __name__ == "__main__":
    get_config()