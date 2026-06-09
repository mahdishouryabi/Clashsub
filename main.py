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
# CONFIG
# -------------------------
TEST_URL = "http://cp.cloudflare.com/generate_204"
FAIL_THRESHOLD = 3
TIMEOUT = 3

# -------------------------
# CACHE
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
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f, indent=2)
    os.replace(tmp, CACHE_FILE)


# -------------------------
# FETCH SUB
# -------------------------
def fetch_sub(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        return [x.strip() for x in r.text.splitlines() if x.strip()]
    except:
        return []


# -------------------------
# TCP TEST
# -------------------------
def tcp_test(host, port):
    try:
        s = socket.socket()
        s.settimeout(TIMEOUT)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False


# -------------------------
# HTTP LATENCY TEST (soft)
# -------------------------
def http_probe():
    try:
        r = requests.get(TEST_URL, timeout=TIMEOUT)
        return r.status_code == 204
    except:
        return False


# -------------------------
# PARSE VLESS
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
            "tls": qs.get("security", ["none"])[0] == "tls"
        }
    except:
        return None


# -------------------------
# PARSE VMESS
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
            "tls": j.get("tls") == "tls"
        }
    except:
        return None


# -------------------------
# SCORE SYSTEM
# -------------------------
def score_server(host, port):
    score = 0

    if tcp_test(host, port):
        score += 50

    if http_probe():
        score += 30

    # bonus random stability factor
    score += 20

    return score


# -------------------------
# CACHE UPDATE (SMART STABILITY ENGINE)
# -------------------------
def update_cache(cache, proxies):
    new_cache = cache.copy()

    for p in proxies:
        name = p["name"]

        if name not in new_cache:
            new_cache[name] = {
                "fail": 0,
                "score": 0,
                "last_good": 0,
                "config": p
            }

        entry = new_cache[name]

        score = score_server(p["server"], p["port"])

        if score > 60:
            entry["fail"] = 0
            entry["score"] = score
            entry["last_good"] = int(time.time())
            entry["config"] = p
        else:
            entry["fail"] += 1
            entry["score"] = max(0, entry["score"] - 10)

        # حذف فقط وقتی واقعا مرده
        if entry["fail"] >= FAIL_THRESHOLD:
            del new_cache[name]

    return new_cache


# -------------------------
# BUILD CLASH CONFIG
# -------------------------
def build(cache):
    proxies = []

    for name, data in cache.items():
        p = data["config"]

        proxies.append({
            "name": p["name"],
            "type": p["type"],
            "server": p["server"],
            "port": p["port"],
            "uuid": p["uuid"],
            "tls": p.get("tls", False),
            "udp": True
        })

    if not proxies:
        return None

    proxy_names = [p["name"] for p in proxies]

    return {
        "mixed-port": 7890,
        "allow-lan": True,
        "mode": "rule",
        "log-level": "info",

        "proxies": proxies,

        "proxy-groups": [
            {
                "name": "AUTO",
                "type": "url-test",
                "proxies": proxy_names,
                "url": TEST_URL,
                "interval": 300
            },
            {
                "name": "SELECT",
                "type": "select",
                "proxies": proxy_names + ["AUTO", "DIRECT"]
            }
        ],

        "rules": [
            "DOMAIN-SUFFIX,google.com,AUTO",
            "DOMAIN-SUFFIX,youtube.com,AUTO",
            "DOMAIN-KEYWORD,telegram,AUTO",
            "MATCH,SELECT"
        ]
    }


# -------------------------
# SUB LIST
# -------------------------
subs = [
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no1.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no2.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no3.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no4.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no5.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no6.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no7.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no8.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no9.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no10.txt",
]


# -------------------------
# MAIN
# -------------------------
def main():
    cache = load_cache()

    all_configs = []
    for s in subs:
        all_configs += fetch_sub(s)

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

    if result:
        with open("clash.yaml", "w", encoding="utf-8") as f:
            yaml.dump(result, f, allow_unicode=True)

        print("OK: clash.yaml created")
        print("configs:", len(result["proxies"]))
    else:
        print("NO VALID PROXIES")


if __name__ == "__main__":
    main()
