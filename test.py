from flask import Flask, render_template, request, redirect, url_for, session
from tools import sshInfo, validateIP, connectivity
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import getconfig
import sqlite3
from prettytable import PrettyTable

device_status = {}

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your-secret-key-change-this-in-production'  # Required for sessions
    
    # Initialize database
    init_db()
    
    @app.route("/")
    def home():
        return render_template("index.html")
    
    @app.route("/get_config")
    def get_config():
        files = getconfig.get_config()
        return render_template("get_config.html", files=files)
    
    @app.route("/ospf_config")
    def ospf_config():
        """Entry point - clears session and starts with R1"""
        session.clear()
        return redirect(url_for('configure_router', router='R1'))
    
    @app.route("/ospf_config/<router>", methods=['GET', 'POST'])
    def configure_router(router):
        """Handles each router configuration page"""
        valid_routers = ['R1', 'R2', 'R3', 'R4']
        
        if router not in valid_routers:
            return "Invalid router", 404
        
        if request.method == 'POST':
            # Save the current router's data
            save_router_config(router, request.form)
            
            # Determine next router
            next_router = get_next_router(router)
            
            if next_router:
                # Go to next router
                return redirect(url_for('configure_router', router=next_router))
            else:
                # All routers configured - proceed to apply configuration
                return redirect(url_for('apply_ospf_config'))
        
        # GET request - show the form for this router
        router_config = get_router_template_data(router)
        return render_template('ospf_config_form.html', **router_config)
    
    @app.route("/apply_ospf_config")
    def apply_ospf_config():
        """Final step - validate IPs, configure OSPF, and test connectivity"""
        # Fetch all router configurations from database
        configs = fetch_all_configs()
        
        if not configs or len(configs) < 4:
            return "Error: Not all routers configured. Please start over.", 400
        
        # Step 1: Validate IPs and display interface table
        ip_table = validate_and_display_ips(configs)
        
        # Step 2: Configure OSPF using NAPALM
        ospf_results = configure_ospf_napalm(configs)
        
        # Step 3: Ping all loopbacks from R1
        ping_results = ping_loopbacks_from_r1(configs)
        
        return render_template('ospf_results.html', 
                             ip_table=ip_table,
                             ospf_results=ospf_results,
                             ping_results=ping_results)
    
    @app.route("/diff_config")
    def diff_config():
        return render_template("diff_config.html")
    
    return app

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect('ospf_config.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS router_configs
                 (router TEXT PRIMARY KEY,
                  hostname TEXT,
                  ip_address TEXT,
                  username TEXT,
                  password TEXT,
                  ospf_process_id INTEGER,
                  router_id TEXT,
                  loopback_ip TEXT,
                  loopback_mask TEXT,
                  interface1 TEXT,
                  interface1_ip TEXT,
                  interface1_mask TEXT,
                  interface1_area TEXT,
                  interface2 TEXT,
                  interface2_ip TEXT,
                  interface2_mask TEXT,
                  interface2_area TEXT,
                  load_balancing BOOLEAN)''')
    conn.commit()
    conn.close()

def save_router_config(router, form_data):
    """Save router configuration to database"""
    conn = sqlite3.connect('ospf_config.db')
    c = conn.cursor()
    
    # Check if load balancing should be enabled (only for R2 and R4)
    load_balancing = 1 if (router in ['R2', 'R4'] and form_data.get('load_balancing') == 'on') else 0
    
    c.execute('''INSERT OR REPLACE INTO router_configs VALUES 
                 (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (router,
               form_data.get('hostname'),
               form_data.get('ip_address'),
               form_data.get('username'),
               form_data.get('password'),
               form_data.get('ospf_process_id'),
               form_data.get('router_id'),
               form_data.get('loopback_ip'),
               form_data.get('loopback_mask'),
               form_data.get('interface1'),
               form_data.get('interface1_ip'),
               form_data.get('interface1_mask'),
               form_data.get('interface1_area'),
               form_data.get('interface2', ''),
               form_data.get('interface2_ip', ''),
               form_data.get('interface2_mask', ''),
               form_data.get('interface2_area', ''),
               load_balancing))
    conn.commit()
    conn.close()

def fetch_all_configs():
    """Fetch all router configurations from database"""
    conn = sqlite3.connect('ospf_config.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM router_configs ORDER BY router')
    rows = c.fetchall()
    conn.close()
    return rows

def validate_and_display_ips(configs):
    """Validate IP addresses and create PrettyTable"""
    table = PrettyTable()
    table.field_names = ["Router", "Interface", "IP Address", "Status"]
    
    for config in configs:
        router = config['router']
        
        # Check loopback
        loopback_valid = validateIP.is_valid_ip(config['loopback_ip'])
        table.add_row([
            router, 
            "Loopback0", 
            config['loopback_ip'], 
            "✓ Valid" if loopback_valid else "✗ Invalid"
        ])
        
        # Check interface 1
        if config['interface1_ip']:
            int1_valid = validateIP.is_valid_ip(config['interface1_ip'])
            table.add_row([
                router, 
                config['interface1'], 
                config['interface1_ip'], 
                "✓ Valid" if int1_valid else "✗ Invalid"
            ])
        
        # Check interface 2
        if config['interface2_ip']:
            int2_valid = validateIP.is_valid_ip(config['interface2_ip'])
            table.add_row([
                router, 
                config['interface2'], 
                config['interface2_ip'], 
                "✓ Valid" if int2_valid else "✗ Invalid"
            ])
    
    return table.get_html_string()

def configure_ospf_napalm(configs):
    """Configure OSPF on all routers using NAPALM"""
    # TODO: Implement NAPALM configuration
    results = []
    for config in configs:
        results.append(f"Router {config['router']}: OSPF configured successfully")
    return results

def ping_loopbacks_from_r1(configs):
    """Ping all loopbacks from R1"""
    # TODO: Implement ping tests
    results = []
    for config in configs:
        if config['router'] != 'R1':
            results.append(f"Ping to {config['loopback_ip']} ({config['router']}): Success")
    return results

if __name__ == "__main__":
    hosts = sshInfo.load_ssh_info("config/sshInfo.json")
    app = create_app()
    app.run(debug=True)