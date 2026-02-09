from napalm import get_network_driver
import sqlite3
from prettytable import PrettyTable
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from tools import connectivity, validateIP

# Thread-safe lock for printing
print_lock = threading.Lock()

def init_db():
    """Initialize SQLite database"""
    with sqlite3.connect('ospf_config.db') as conn:
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
                    interface2_area TEXT)''')
        conn.commit()

def save_router_config(router, form_data):
    """Save router configuration to database"""
    with sqlite3.connect('ospf_config.db') as conn:
        c = conn.cursor()
        
        c.execute('''INSERT OR REPLACE INTO router_configs VALUES 
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
                form_data.get('interface2_area', '')))
        conn.commit()

def fetch_all_configs():
    """Fetch all router configurations from database"""
    with sqlite3.connect('ospf_config.db') as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM router_configs ORDER BY router')
        rows = c.fetchall()

    return rows

def get_router_template_data(router):
    """Returns router-specific configuration data for the template"""
    
    base_config = {
        'router': router,
        'next_router': get_next_router(router),
        'fields': [
            {
                'name': 'hostname', 
                'label': 'Hostname', 
                'type': 'text', 
                'required': True, 
                'placeholder': f'{router}'
            },
            {
                'name': 'ip_address', 
                'label': 'Management IP Address', 
                'type': 'text', 
                'required': True, 
                'placeholder': '192.168.1.1'
            },
            {
                'name': 'username', 
                'label': 'SSH Username', 
                'type': 'text', 
                'required': True, 
                'placeholder': 'admin'
            },
            {
                'name': 'password', 
                'label': 'SSH Password', 
                'type': 'password', 
                'required': True
            },
            {
                'name': 'ospf_process_id', 
                'label': 'OSPF Process ID', 
                'type': 'number', 
                'required': True, 
                'value': '1'
            },
            {
                'name': 'router_id', 
                'label': 'OSPF Router ID', 
                'type': 'text', 
                'required': True, 
            },
            {
                'name': 'loopback_ip', 
                'label': 'Loopback IP Address', 
                'type': 'text', 
                'required': True, 
            },
            {
                'name': 'loopback_mask', 
                'label': 'Loopback Subnet Mask', 
                'type': 'text', 
                'required': True, 
                'value': '255.255.255.255'
            },
        ],
        'interfaces': [
            {
                'number': 1,
                'fields': [
                    {
                        'name': 'interface1', 
                        'label': 'Interface Name', 
                        'type': 'text', 
                        'required': True, 
                        'placeholder': 'GigabitEthernet0/0'
                    },
                    {
                        'name': 'interface1_ip', 
                        'label': 'IP Address', 
                        'type': 'text', 
                        'required': True, 
                        'placeholder': '10.0.0.1'
                    },
                    {
                        'name': 'interface1_mask', 
                        'label': 'Subnet Mask', 
                        'type': 'text', 
                        'required': True, 
                        'value': '255.255.255.0'
                    },
                    {
                        'name': 'interface1_area', 
                        'label': 'OSPF Area', 
                        'type': 'text', 
                        'required': True, 
                        'value': '0'
                    },
                ]
            },
            {
                'number': 2,
                'fields': [
                    {
                        'name': 'interface2', 
                        'label': 'Interface Name', 
                        'type': 'text', 
                        'required': False, 
                        'placeholder': 'GigabitEthernet0/1'
                    },
                    {
                        'name': 'interface2_ip', 
                        'label': 'IP Address', 
                        'type': 'text', 
                        'required': False, 
                        'placeholder': '10.0.1.1'
                    },
                    {
                        'name': 'interface2_mask', 
                        'label': 'Subnet Mask', 
                        'type': 'text', 
                        'required': False, 
                        'value': '255.255.255.0'
                    },
                    {
                        'name': 'interface2_area', 
                        'label': 'OSPF Area', 
                        'type': 'text', 
                        'required': False, 
                        'value': '0'
                    },
                ]
            }
        ]
    }
    
    # Router-specific area customizations based on typical inter-area OSPF topology
    if router == 'R2':
        base_config['interfaces'][1]['fields'][3]['value'] = '1'  # Interface 2 in Area 1
    elif router == 'R3':
        base_config['interfaces'][0]['fields'][3]['value'] = '1'  # Interface 1 in Area 1
        base_config['interfaces'][1]['fields'][3]['value'] = '2'  # Interface 2 in Area 2
    elif router == 'R4':
        base_config['interfaces'][0]['fields'][3]['value'] = '2'  # Interface 1 in Area 2
    
    return base_config

def get_next_router(current):
    """Get the next router in sequence"""
    routers = ['R1', 'R2', 'R3', 'R4']
    try:
        idx = routers.index(current)
        return routers[idx + 1] if idx < len(routers) - 1 else None
    except ValueError:
        return None

def ping_loopbacks_from_r1(configs):
    """Ping all loopback IPs from R1"""
    
    r1_config = None
    for config in configs:
        if config['router'] == 'R1':
            r1_config = config
            break
    
    if not r1_config:
        return {'success': False, 'results': [], 'error': 'R1 not found'}
    
    results = []
    
    try:
        driver = get_network_driver("ios")
        device = driver(
            hostname=r1_config['ip_address'],
            username=r1_config['username'],
            password=r1_config['password'],
            optional_args={'read_timeout_override': 60}
        )
        device.open()
        
        for config in configs:
            if config['router'] != 'R1':
                ping_cmd = f"ping {config['loopback_ip']} repeat 5"
                output = device.cli([ping_cmd])[ping_cmd]
                success = "100 percent" in output
                
                results.append({
                    'router': config['router'],
                    'ip': config['loopback_ip'],
                    'status': 'Success' if success else 'Failed'
                })
        
        device.close()
        return {'success': True, 'results': results}
        
    except Exception as e:
        return {'success': False, 'results': [], 'error': str(e)}

def configure_single_router(config):
    """Configure OSPF on a single router"""
    router = config['router']
    
    try:
        with print_lock:
            print(f"Configuring {router}...")
        
        # Configure with napalm
        driver = get_network_driver("ios")
        device = driver(
            hostname=config['ip_address'],
            username=config['username'],
            password=config['password']
        )
        device.open()
        
        # Build OSPF configuration
        ospf_config = (
            f"router ospf {config['ospf_process_id']}\n"
            f" router-id {config['router_id']}\n"
            f" network {config['loopback_ip']} 0.0.0.0 area {config['interface1_area']}\n"
            f" network {config['interface1_ip']} {config['interface1_mask']} area {config['interface1_area']}\n"
        )
        
        # Add second interface if it exists
        if config['interface2'] and config['interface2_ip']:
            ospf_config += (
                f" network {config['interface2_ip']} {config['interface2_mask']} "
                f"area {config['interface2_area']}\n"
            )
        
        with print_lock:
            print(f"  Loading configuration for {router}...")
        device.load_merge_candidate(config=ospf_config)
        
        with print_lock:
            print(f"  Committing configuration for {router}...")
        device.commit_config()
        
        device.close()
        
        with print_lock:
            print(f"  ✓ {router} configured successfully\n")
        
        return {'router': router, 'success': True}
        
    except Exception as e:
        with print_lock:
            print(f"  ✗ Error configuring {router}: {str(e)}\n")
        return {'router': router, 'success': False}

def configure_ospf(configs):
    """Configure OSPF on the routers"""
    
    # Create PrettyTable for IP validation results
    ip_table = PrettyTable()
    ip_table.field_names = ["Router", "Interface", "IP Address", "Subnet Mask", "Valid", "Reachable"]
    
    # First pass: Validate all IPs and populate table
    print("\n" + "="*80)
    print("VALIDATING IP ADDRESSES AND CHECKING REACHABILITY")
    print("="*80 + "\n")
    
    all_reachable = True
    
    for config in configs:
        router = config['router']
        
        # Validate and check Management IP
        mgmt_valid = validateIP.validate_ip(config['ip_address'])
        reach = connectivity.check_reachability([config['ip_address']])
        mgmt_reachable = reach[config['ip_address']]
        
        ip_table.add_row([
            router,
            "Management",
            config['ip_address'],
            "N/A",
            "✓" if mgmt_valid else "✗",
            "✓" if mgmt_reachable else "✗"
        ])
        
        if not mgmt_reachable:
            all_reachable = False
        
        # Validate Loopback IP
        loopback_valid = validateIP.validate_ip(config['loopback_ip'])
        ip_table.add_row([
            router,
            "Loopback0",
            config['loopback_ip'],
            config['loopback_mask'],
            "✓" if loopback_valid else "✗",
            "N/A"
        ])
        
        # Validate Interface 1 IP
        int1_valid = validateIP.validate_ip(config['interface1_ip'])
        ip_table.add_row([
            router,
            config['interface1'],
            config['interface1_ip'],
            config['interface1_mask'],
            "✓" if int1_valid else "✗",
            "N/A"
        ])
        
        # Validate Interface 2 IP (if exists)
        if config['interface2'] and config['interface2_ip']:
            int2_valid = validateIP.validate_ip(config['interface2_ip'])
            ip_table.add_row([
                router,
                config['interface2'],
                config['interface2_ip'],
                config['interface2_mask'],
                "✓" if int2_valid else "✗",
                "N/A"
            ])
    
    # Print the table
    print(ip_table)
    print("\n")
    
    # Check if all management IPs are reachable before proceeding
    if not all_reachable:
        print("ERROR: Not all routers are reachable. Cannot proceed with OSPF configuration.")
        return False
    
    # Second pass: Configure OSPF on each router using ThreadPoolExecutor
    print("="*80)
    print("CONFIGURING OSPF ON ROUTERS (PARALLEL)")
    print("="*80 + "\n")
    
    # Use executor.map() - much simpler!
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(configure_single_router, configs))
    
    # Check if all succeeded
    all_success = all(r['success'] for r in results)

    if all_success:
        # Wait for OSPF convergence
        print("Waiting for OSPF convergence...", end="", flush=True)
        time.sleep(60)  # Wait 30 seconds
        print(" Done!\n")

    
    print("="*80)
    print("OSPF CONFIGURATION COMPLETE")
    print("="*80 + "\n")
    
    return all_success