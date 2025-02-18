import requests
import random
import string


def get_public_ip():
    try:
        ip = requests.get("https://api.ipify.org").text.strip()
        return ip
    except Exception as e:
        print("获取公网 IP 失败:", e)
        return "0.0.0.0"


# 生成随机秘钥的函数（用于登录验证）
def generate_secret_key(length=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))
