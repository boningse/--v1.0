import xml.etree.ElementTree as ET
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_CONFIG_PATH = os.path.join(BASE_DIR, "web.config")

def parse_connection_strings():
    tree = ET.parse(WEB_CONFIG_PATH)
    connections = {}
    for add_elem in tree.findall(".//connectionStrings/add"):
        name = add_elem.get("name")
        conn_str = add_elem.get("connectionString")
        params = {}
        for part in conn_str.split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key.strip()] = value.strip()
        connections[name] = {
            "host": params.get("Data Source", "localhost"),
            "port": int(params.get("port", 3306)),
            "user": params.get("uid", ""),
            "password": params.get("pwd", ""),
            "database": params.get("Initial Catalog", ""),
            "charset": "utf8",
        }
    return connections

DB_CONNECTIONS = parse_connection_strings()
