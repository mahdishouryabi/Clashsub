import requests
import yaml
import base64
import json
import time
import os
import socket
from urllib.parse import urlparse, parse_qs

CACHE_FILE = "cache.json"

TEST_TIMEOUT = 3
FAIL_THRESHOLD = 3
MIN_KEEP = 10  # همیشه حداقل ۱۰ کانفیگ نگه دار

TEST_URL = "http://www.gstatic.com/generate_204"


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
# FETCH
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
# TEST (SOFT)
# -------------------------
def test_server(host, port):
    try:
        s = socket.socket()
        s.settimeout(TEST_TIMEOUT)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False


# -------------------------
# PARSERS
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
# CACHE UPDATE (FIXED)
# -------------------------
def update_cache(cache, proxies):
    new_cache = cache.copy()

    for p in proxies:
        name = p["name"]

        if name not in new_cache:
            new_cache[name] = {
                "fail": 0,
                "config": p,
                "last_good": 0,
                "last_seen": int(time.time())
            }

        entry = new_cache[name]
        ok = test_server(p["server"], p["port"])

        if ok:
            entry["fail"] = 0
            entry["config"] = p
            entry["last_good"] = int(time.time())
        else:
            entry["fail"] += 1

        entry["last_seen"] = int(time.time())

    # ❌ فقط اگر خیلی خراب شد حذف کن، ولی حداقل ۱۰ تا نگه دار
    if len(new_cache) > MIN_KEEP:
        to_delete = [
            k for k, v in new_cache.items()
            if v["fail"] >= FAIL_THRESHOLD
        ]
        for k in to_delete:
            del new_cache[k]

    return new_cache


# -------------------------
# CLASH BUILDER
# -------------------------
def build_clash(cache):
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

    names = [p["name"] for p in proxies]

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
                "proxies": names,
                "url": TEST_URL,
                "interval": 120
            },
            {
                "name": "SELECT",
                "type": "select",
                "proxies": names + ["AUTO", "DIRECT"]
            }
        ],

        "rules": [
            "MATCH,SELECT"
        ]
    }


# -------------------------
# V2RAYNG (FIXED)
# -------------------------
def build_v2rayng(cache):
    lines = []

    for name, data in cache.items():
        p = data["config"]

        if p["type"] == "vless":
            link = f"vless://{p['uuid']}@{p['server']}:{p['port']}?security={'tls' if p.get('tls') else 'none'}#{p['name']}"
            lines.append(link)

        elif p["type"] == "vmess":
            vm = {
                "v": "2",
                "ps": p["name"],
                "add": p["server"],
                "port": str(p["port"]),
                "id": p["uuid"],
                "net": "tcp",
                "tls": "tls" if p.get("tls") else ""
            }
            encoded = base64.b64encode(json.dumps(vm).encode()).decode()
            lines.append("vmess://" + encoded)

    return base64.b64encode("\n".join(lines).encode()).decode()


# -------------------------
# MAIN
# -------------------------
def main():
    subs = [
        "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no1.txt",
        "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no2.txt",
        "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no3.txt",
        "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no4.txt",
        "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no5.txt",
    ]

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

    clash = build_clash(cache)
    v2rayng = build_v2rayng(cache)

    if clash:
        with open("clash.yaml", "w") as f:
            yaml.dump(clash, f, allow_unicode=True)

    if v2rayng:
        with open("v2rayng_sub.txt", "w") as f:
            f.write(v2rayng)

    print("DONE")
    print("TOTAL:", len(cache))


if __name__ == "__main__":
    main()
