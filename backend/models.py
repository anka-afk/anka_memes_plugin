import os
import shutil
from werkzeug.utils import secure_filename

BASE_DIR = "./memes"


# 扫描所有类别和表情包
def scan_emoji_folder():
    emoji_data = {}
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
    for category in os.listdir(BASE_DIR):
        category_path = os.path.join(BASE_DIR, category)
        if os.path.isdir(category_path):
            emoji_files = [
                f
                for f in os.listdir(category_path)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
            ]
            emoji_data[category] = emoji_files
    return emoji_data


# 获取指定类别下的所有表情包
def get_emoji_by_category(category):
    category_path = os.path.join(BASE_DIR, category)
    if not os.path.isdir(category_path):
        return None
    emoji_files = [
        f
        for f in os.listdir(category_path)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
    ]
    return emoji_files


# 添加表情包到指定类别
def add_emoji_to_category(category, image_file):
    category_path = os.path.join(BASE_DIR, category)
    if not os.path.exists(category_path):
        os.makedirs(category_path)
    # 使用 secure_filename 确保文件名安全
    filename = secure_filename(image_file.filename)
    target_path = os.path.join(category_path, filename)
    image_file.save(target_path)
    return target_path


# 删除指定类别下的表情包
def delete_emoji_from_category(category, image_file):
    category_path = os.path.join(BASE_DIR, category)
    if not os.path.isdir(category_path):
        return False
    image_path = os.path.join(category_path, image_file)
    if os.path.exists(image_path):
        os.remove(image_path)
        return True
    return False


# 更新（替换）表情包文件
def update_emoji_in_category(category, old_image_file, new_image_file):
    category_path = os.path.join(BASE_DIR, category)
    if not os.path.isdir(category_path):
        return False
    old_image_path = os.path.join(category_path, old_image_file)
    if os.path.exists(old_image_path):
        os.remove(old_image_path)
        filename = secure_filename(new_image_file.filename)
        target_path = os.path.join(category_path, filename)
        new_image_file.save(target_path)
        return True
    return False
