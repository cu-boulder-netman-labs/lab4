from flask import Flask, render_template, redirect, url_for, request
from tools import sshInfo, validateIP, connectivity
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import getconfig
import ospfconfig
import diffconfig
import migration

device_status = {}

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/get_config")
    def get_config():
        files = getconfig.get_config()
        return render_template("get_config.html", files=files)

    @app.route("/ospf_config")
    def ospf_config():
        return redirect(url_for('configure_router', router='R1'))

    @app.route("/ospf_config/<router>", methods=['GET', 'POST'])
    def configure_router(router):
        valid_routers = ['R1', 'R2', 'R3', 'R4']

        # Ensure only valid routers get configured
        if router not in valid_routers:
            return "Invalid router", 404
        
        if request.method == 'POST':
            # Save the current router's data
            ospfconfig.save_router_config(router, request.form)
            
            # Determine next router
            next_router = ospfconfig.get_next_router(router)
            
            if next_router:
                # Go to next router
                return redirect(url_for('configure_router', router=next_router))
            else:
                # All routers configured - proceed to apply configuration
                return redirect(url_for('apply_ospf_config'))

        # GET
        router_config = ospfconfig.get_router_template_data(router)
        return render_template('ospf_config_form.html', **router_config)

    @app.route("/apply_ospf_config")
    def apply_ospf_config():
        """Final step - validate IPs, configure OSPF, and test connectivity"""
        # Fetch all router configurations from database
        configs = ospfconfig.fetch_all_configs()
        
        if not configs or len(configs) < 4:
            return "Error: Not all routers configured. Please start over.", 400

        ospfconfig.configure_ospf(configs)
        
        ping_results = ospfconfig.ping_loopbacks_from_r1(configs)
        
        return render_template('ospf_results.html', ping_results=ping_results)

    @app.route("/diff_config")
    def diff_config():
        diff_results = diffconfig.diff_config()
        return render_template("diff_config.html", diff_results=diff_results)

    @app.route("/migrate")
    def migrate():
        result = migration.migrate()
        return render_template("migrate.html", result=result)

    return app


if __name__ == "__main__":
    hosts = sshInfo.load_ssh_info("config/sshInfo.json")

    ospfconfig.init_db()
    app = create_app()
    app.run(debug=True)
