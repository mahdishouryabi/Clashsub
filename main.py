import requests
import yaml
import base64
import json
import time
import os
import socket
from urllib.parse import urlparse, parse_qs

CACHE_FILE = "cache.json"

# -------------------------
# LOAD CACHE
# -------------------------
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


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
# SMART TEST (3 STRIKE RULE)
# -------------------------
def test_server(host, port, timeout=2):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except:
        return False


# -------------------------
# VLESS
# -------------------------
def parse_vless(link, name):
    try:
        p = urlparse(link)
        uuid, hp = p.netloc.split("@")
        host, port = hp.split(":")
        qs = parse_qs(p.query)

        return {
            "name": name,
            "type": "vless",
            "server": host,
            "port": int(port),
            "uuid": uuid,
            "tls": qs.get("security", ["none"])[0] == "tls",
        }
    except:
        return None


# -------------------------
# VMESS
# -------------------------
def parse_vmess(link, name):
    try:
        data = link.replace("vmess://", "")
        decoded = base64.b64decode(data + "==").decode()
        j = json.loads(decoded)

        return {
            "name": name,
            "type": "vmess",
            "server": j["add"],
            "port": int(j["port"]),
            "uuid": j["id"],
            "tls": j.get("tls") == "tls",
        }
    except:
        return None


# -------------------------
# UPDATE CACHE (SMART LOGIC)
# -------------------------
def update_cache(cache, proxies):
    updated = {}

    for p in proxies:
        name = p["name"]

        if name in cache:
            entry = cache[name]
        else:
            entry = {
                "fail": 0,
                "config": p,
                "last_good": 0
            }

        host = p["server"]
        port = p["port"]

        if test_server(host, port):
            entry["fail"] = 0
            entry["last_good"] = int(time.time())
            entry["config"] = p
        else:
            entry["fail"] += 1

        # ❌ حذف فقط اگر 3 بار پشت هم fail شد
        if entry["fail"] < 3:
            updated[name] = entry

    return updated


# -------------------------
# BUILD YAML
# -------------------------
def build(cache):
    proxies = []

    for name, data in cache.items():
        proxies.append(data["config"])

    if not proxies:
        return None

    return {
        "mixed-port": 7890,
        "allow-lan": True,
        "mode": "rule",
        "log-level": "info",

        "proxies": proxies,

        "proxy-groups": [
            {
                "name": "auto",
                "type": "select",
                "proxies": [p["name"] for p in proxies] + ["DIRECT"]
            }
        ],

        "rules": [
            "DOMAIN-SUFFIX,google.com,auto",
            "DOMAIN-SUFFIX,youtube.com,auto",
            "DOMAIN-KEYWORD,telegram,auto",
            "MATCH,auto"
        ]
    }


# -------------------------
# SUB LIST
# -------------------------
subs = [
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no1.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no2.txt",
]


# -------------------------
# MAIN
# -------------------------
cache = load_cache()

all_configs = []
for s in subs:
    all_configs.extend(fetch_sub(s))

all_configs = list(set(all_configs))

proxies = []

for i, c in enumerate(all_configs):
    p = None

    if c.startswith("vless://"):
        p = parse_vless(c, f"proxy-{i}")
    elif c.startswith("vmess://"):
        p = parse_vmess(c, f"proxy-{i}")

    if p:
        proxies.append(p)

cache = update_cache(cache, proxies)
save_cache(cache)

result = build(cache)

# -------------------------
# SAVE
# -------------------------
if result:
    path = "clash.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(result, f, allow_unicode=True)

    print("OK: clash.yaml created")
    print("configs:", len(result["proxies"]))
else:
    print("NO VALID PROXIES")
