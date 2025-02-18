import requests
import hashlib
import random
import time
import string
import os
from .image_host import ImageHost


class StarDotsImageHost(ImageHost):
    STARDOTS_API_BASE = "https://api.stardots.io"
    STARDOTS_KEY = "your_stardots_key"  # 替换为你的 StarDots Key
    STARDOTS_SECRET = "your_stardots_secret"  # 替换为你的 StarDots Secret

    def _generate_headers(self):
        """
        根据 StarDots API 生成鉴权 header
        """
        timestamp = str(int(time.time()))
        nonce = "".join(random.choices(string.ascii_letters + string.digits, k=10))
        sign_str = f"{timestamp}|{self.STARDOTS_SECRET}|{nonce}"
        sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

        return {
            "x-stardots-timestamp": timestamp,
            "x-stardots-nonce": nonce,
            "x-stardots-key": self.STARDOTS_KEY,
            "x-stardots-sign": sign,
        }

    def create_space(self, space: str) -> dict:
        url = f"{self.STARDOTS_API_BASE}/openapi/space/create"
        payload = {"space": space, "public": False}
        headers = self._generate_headers()
        response = requests.put(url, json=payload, headers=headers)
        return response.json()

    def upload_file(self, space: str, file_path: str) -> dict:
        url = f"{self.STARDOTS_API_BASE}/openapi/file/upload"
        headers = self._generate_headers()

        with open(file_path, "rb") as f:
            files = {"file": (file_path, f)}
            data = {"space": space}
            response = requests.put(url, data=data, files=files, headers=headers)

        return response.json()

    def sync_memes_to_host(self, memes_dir: str) -> dict:
        results = {}
        for category in os.listdir(memes_dir):
            category_path = os.path.join(memes_dir, category)
            if os.path.isdir(category_path):
                create_resp = self.create_space(category)
                results[category] = {"create_space": create_resp, "files": {}}
                for file_name in os.listdir(category_path):
                    file_path = os.path.join(category_path, file_name)
                    if os.path.isfile(file_path):
                        upload_resp = self.upload_file(category, file_path)
                        results[category]["files"][file_name] = upload_resp
        return results
