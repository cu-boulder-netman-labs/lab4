from flask import Flask, render_template
from tools import sshInfo, validateIP, connectivity
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import getconfig

device_status = {}

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/get_config")
    def get_config():
        cfg_files = getconfig.get_config()
        return render_template("get_config.html")

    @app.route("/ospf_config")
    def ospf_config():
        return render_template("ospf_config.html")

    @app.route("/diff_config")
    def diff_config():
        return render_template("diff_config.html")

    return app


if __name__ == "__main__":
    hosts = sshInfo.load_ssh_info("config/sshInfo.json")

    app = create_app()
    app.run(debug=True)
