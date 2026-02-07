import subprocess
from subprocess import CalledProcessError, TimeoutExpired


def check_reachability(hosts: list) -> dict:
    """
    Checks if hosts are reachable via ping.

    Args:
        hosts: a list of hosts to check

    Returns:
        Dictionary of hosts reachable via ping.
    """
    results = {}

    for host in hosts:
        try:
            subprocess.run(
                ["ping", "-c", "1", host],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            results[host] = True
        except CalledProcessError:
            results[host] = False
            print(f'{host} unreachable')
        except TimeoutExpired:
            results[host] = False
            print(f'{host} timed out')

    return results


if __name__ == '__main__':
    hosts = [
        "8.8.8.8",
        "198.51.100.1",
        "198.51.100.5",
        "198.51.100.3",
    ]
    print(check_reachability(hosts))

