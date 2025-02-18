import requests
import random
import string
import socket
from typing import Optional


def get_public_ip() -> Optional[str]:

    endpoints = [
        {"url": "https://api.ipify.org", "timeout": 3},
        {"url": "https://checkip.amazonaws.com", "timeout": 3},
        {"url": "https://ident.me", "timeout": 3},
        {"url": "http://icanhazip.com", "timeout": 3},
        {"url": "https://ifconfig.me/ip", "timeout": 5},
    ]

    for ep in endpoints:
        try:
            resp = requests.get(
                ep["url"],
                timeout=ep["timeout"],
                proxies={"http": None, "https": None},
                headers={"Host": socket.gethostbyname(ep["url"].split("/")[2])},
            )
            resp.raise_for_status()
            ip = resp.text.strip()
            if "." in ip or ":" in ip:
                return ip
        except requests.exceptions.RequestException as e:
            print(f"API [{ep['url']}] 失败: {type(e).__name__} - {str(e)}")
            continue

    print("所有API端点均不可用")
    return None


def generate_secret_key(length=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))
