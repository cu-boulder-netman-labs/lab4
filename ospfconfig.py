import sqlite3
from tools import connectivity, validateIP

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
                    interface2_area TEXT,
                    load_balancing BOOLEAN)''')
        conn.commit()

def save_router_config(router, form_data):
    """Save router configuration to database"""
    with sqlite3.connect('ospf_config.db') as conn:
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
        'show_load_balancing': router in ['R2', 'R4'],
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

def configure(configs):
    """Configure OSPF on the routers"""
    for config in configs:
        # Validate IPs and reachability
        validateIP.

