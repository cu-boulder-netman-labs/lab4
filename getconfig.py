import napalm
from tools import sshInfo, validateIP, connectivity
from concurrent.futures import ThreadPoolExecutor

def check_device(device):
    host = device['host']

    if not validateIP.validate_ip(host):
        return host, "invalid ip"

    reachable = connectivity.check_reachability([host])
    return host, "reachable" if reachable[host] else "unreachable"

def get_config():
    hosts = sshInfo.load_ssh_info("config/sshInfo.json")

    with ThreadPoolExecutor() as executor:
        results = executor.map(check_device, hosts)

    for host in hosts:
        driver = napalm.get_network_driver('ios')
        device = driver(
            hostname=host['host'],
            username=host['username'],
            password=host['password'],
        )

        device.open()

        cfg = device.get_config()
        with open(f"{host['host']}_running.cfg", 'w') as f:
            f.write(cfg["running"])
        print(cfg)

        device.close()

if __name__ == "__main__":
    get_config()