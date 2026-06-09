import requests
import yaml
import json
import base64
from urllib.parse import urlparse, parse_qs

# -------------------------
# FETCH SUB
# -------------------------
def fetch_sub(url):
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return []
        return [x.strip() for x in r.text.splitlines() if x.strip()]
    except:
        return []

# -------------------------
# VLESS PARSER
# -------------------------
def parse_vless(link, name):
    try:
        p = urlparse(link)
        uuid, hp = p.netloc.split("@")
        host, port = hp.split(":")
        qs = parse_qs(p.query)

        proxy = {
            "name": name,
            "type": "vless",
            "server": host,
            "port": int(port),
            "uuid": uuid,
            "udp": True
        }

        if qs.get("security", ["none"])[0] == "tls":
            proxy["tls"] = True
            proxy["servername"] = qs.get("sni", [host])[0]

        if qs.get("type", ["tcp"])[0] == "ws":
            proxy["network"] = "ws"
            proxy["ws-opts"] = {
                "path": qs.get("path", ["/"])[0],
                "headers": {
                    "Host": qs.get("host", [host])[0]
                }
            }

        return proxy
    except:
        return None

# -------------------------
# VMESS PARSER
# -------------------------
def parse_vmess(link, name):
    try:
        data = link.replace("vmess://", "")
        decoded = base64.b64decode(data + "==").decode()
        j = json.loads(decoded)

        proxy = {
            "name": name,
            "type": "vmess",
            "server": j["add"],
            "port": int(j["port"]),
            "uuid": j["id"],
            "udp": True
        }

        if j.get("tls") == "tls":
            proxy["tls"] = True
            proxy["servername"] = j.get("host", j["add"])

        if j.get("net") == "ws":
            proxy["network"] = "ws"
            proxy["ws-opts"] = {
                "path": j.get("path", "/"),
                "headers": {"Host": j.get("host", j["add"])}
            }

        return proxy
    except:
        return None

# -------------------------
# BUILD
# -------------------------
def build(configs):
    proxies = []

    for i, c in enumerate(configs):
        if c.startswith("vless://"):
            p = parse_vless(c, f"proxy-{i}")
        elif c.startswith("vmess://"):
            p = parse_vmess(c, f"proxy-{i}")
        else:
            continue

        if p:
            proxies.append(p)

    if not proxies:
        return None

    return {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",

        "proxies": proxies,

        "proxy-groups": [
            {
                "name": "auto",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "proxies": [p["name"] for p in proxies]
            }
        ],

        "rules": [
            "MATCH,auto"
        ]
    }

# -------------------------
# SUBS
# -------------------------
subs = [
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no1.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no2.txt",
]

all_configs = []
for s in subs:
    all_configs.extend(fetch_sub(s))

all_configs = list(set(all_configs))

result = build(all_configs)

# -------------------------
# SAVE
# -------------------------
if result:
    with open("clash.yaml", "w", encoding="utf-8") as f:
        yaml.dump(result, f, allow_unicode=True)

    print("OK: clash.yaml created")

print("configs:", len(all_configs))
