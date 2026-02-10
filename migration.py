import napalm
import time
from tools import sshInfo
import threading
import sys

def cont_ping(host):
    try:
        driver = napalm.get_network_driver("ios")
        device = driver(
            hostname=host['host'],
            username=host['username'],
            password=host['password'],
            optional_args={'read_timeout_override': 120}
        )
        device.open()

        start = time.time()

        # Issue the ping command
        while (time.time() - start) < 120:
            try:
                ping_cmd = "ping 30.0.0.1 repeat 1"
                output = device.cli([ping_cmd])
                result = output[ping_cmd]

                success = "!" in result or "Success rate is 100" in result

                if success:
                    print(result.splitlines()[3])
                if not success:
                    print("Ping FAILED!")

                # Ping once a second
                time.sleep(1)
            except Exception as e:
                print("Could not ping device:", e)

        device.close()

    except Exception as e:
        print("Failed to connect to device and ping")

def check_interface_traffic(host):
    try:
        driver = napalm.get_network_driver("ios")
        device = driver(
            hostname=host['host'],
            username=host['username'],
            password=host['password'],
            optional_args={'read_timeout_override': 120}
        )
        device.open()

        hostname = device.get_facts()['hostname']
        print(f"Checking for interface traffic on {hostname}, FastEthernet1/0")
        counters = device.get_interfaces_counters()['FastEthernet1/0']

        start_count_tx = counters['tx_unicast_packets']
        start_count_rx = counters['rx_unicast_packets']

        time.sleep(10)

        counters = device.get_interfaces_counters()['FastEthernet1/0']

        end_count_tx = counters['tx_unicast_packets']
        end_count_rx = counters['rx_unicast_packets']

        traffic_present = False
        if end_count_tx - start_count_tx > 100 or end_count_rx - start_count_rx > 100:
            traffic_present = True

        device.close()

    except Exception as e:
        print("failed to check interface traffic", e)

    return traffic_present

def shutdown_iface(host):
    try:
        driver = napalm.get_network_driver("ios")
        device = driver(
            hostname=host['host'],
            username=host['username'],
            password=host['password'],
            optional_args={'read_timeout_override': 120}
        )
        device.open()

        # Shutdown interface
        shutdown_config = f"interface f1/0\n shutdown\n"
        device.load_merge_candidate(config=shutdown_config)
        device.commit_config()
        print(f"Interface f1/0 shutdown, banner configured. Waiting 10s before turning back on...")

        # Configure banner
        banner_config = "banner motd ^Change made for migration in Lab 6^\n"
        device.load_merge_candidate(config=banner_config)
        device.commit_config()
        time.sleep(10)

        no_shutdown_config = f"interface f1/0\n no shutdown\n"
        device.load_merge_candidate(config=no_shutdown_config)
        device.commit_config()
        print(f"Interface f1/0 brought back up")

        device.close()

    except Exception as e:
        print("Failed to shutdown interface", e)


def migrate():
    host = sshInfo.load_ssh_info("config/sshInfo.json")

    # Start continuous ping in background thread
    ping_thread = threading.Thread(
        target=cont_ping, 
        daemon=True,
        args=(host[0],)
    )
    ping_thread.start()

    if check_interface_traffic(host[3]):
        print("Traffic present, cannot continue")
        sys.exit()

    shutdown_iface(host[3])

    print("Successfully migrated!")

    return {'success': True, 'message': 'Migrated successfully'}
    

if __name__ == "__main__":
    migrate()