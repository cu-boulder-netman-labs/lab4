import json
from pathlib import Path

def load_ssh_info(filename: str):
    devices = []

    fpath = Path(filename)
    if not fpath.is_file():
        raise Exception(f"Given filepath was not valid: {filename}")

    with open(fpath, "r") as f:
        data = json.load(f)
        devices = data['routers']

    return devices

if __name__ == "__main__":
    dev = load_ssh_info("sshInfo.json")
    print(dev)