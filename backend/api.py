from flask import Blueprint, jsonify, request
from .models import (
    scan_emoji_folder,
    get_emoji_by_category,
    add_emoji_to_category,
    delete_emoji_from_category,
    update_emoji_in_category,
)
import json
import os
from image_host.stardots_host import StarDotsImageHost

# 创建图床对象，这里你可以动态选择使用哪个图床
# 比如根据配置文件或请求参数决定使用 StarDots 还是其他图床
image_host = StarDotsImageHost()  # 选择 StarDots 图床实现
# image_host = OtherImageHost()  # 或者选择其他图床实现

api = Blueprint("api", __name__)


# 获取所有表情包（按类别分组）
@api.route("/emoji", methods=["GET"])
def get_all_emojis():
    emoji_data = scan_emoji_folder()
    return jsonify(emoji_data)


# 获取指定类别的表情包
@api.route("/emoji/<category>", methods=["GET"])
def get_emojis_by_category(category):
    emojis = get_emoji_by_category(category)
    if emojis is None:
        return jsonify({"message": "Category not found"}), 404
    return jsonify(emojis)


# 添加表情包到指定类别
@api.route("/emoji/add", methods=["POST"])
def add_emoji():
    # 支持 JSON 和 multipart/form-data 两种请求方式
    category = None
    image_file = None
    if "image_file" in request.files:
        image_file = request.files["image_file"]
        category = request.form.get("category")
    else:
        data = request.get_json()
        if data:
            category = data.get("category")
            image_file = data.get("image_file")
    if not category or not image_file:
        return jsonify({"message": "Category and image file are required"}), 400

    # 添加表情包
    try:
        result_path = add_emoji_to_category(category, image_file)
    except Exception as e:
        return jsonify({"message": f"添加表情包失败: {str(e)}"}), 500

    return jsonify({"message": "Emoji added successfully", "path": result_path}), 201


# 删除指定类别的表情包
@api.route("/emoji/delete", methods=["POST"])
def delete_emoji():
    data = request.get_json()
    category = data.get("category")
    image_file = data.get("image_file")
    if not category or not image_file:
        return jsonify({"message": "Category and image file are required"}), 400

    if delete_emoji_from_category(category, image_file):
        return jsonify({"message": "Emoji deleted successfully"}), 200
    else:
        return jsonify({"message": "Emoji not found"}), 404


# 更新指定类别下的表情包
@api.route("/emoji/update", methods=["POST"])
def update_emoji():
    data = request.get_json()
    category = data.get("category")
    old_image_file = data.get("old_image_file")
    new_image_file = data.get("new_image_file")
    if not category or not old_image_file or not new_image_file:
        return (
            jsonify({"message": "Category, old and new image files are required"}),
            400,
        )

    if update_emoji_in_category(category, old_image_file, new_image_file):
        return jsonify({"message": "Emoji updated successfully"}), 200
    else:
        return jsonify({"message": "Emoji not found or update failed"}), 404


# 获取表情包映射的中文-英文名
@api.route("/emotions", methods=["GET"])
def get_emotions():
    try:
        with open("emotions.json", "r", encoding="utf-8") as f:
            emotions = json.load(f)
        return jsonify(emotions)
    except Exception as e:
        return jsonify({"message": f"无法读取 emotions.json: {str(e)}"}), 500


# 添加分类：输入中文键和英文值，同时更新 emotions.json 并创建对应目录
@api.route("/category/add", methods=["POST"])
def add_category():
    data = request.get_json()
    chinese = data.get("chinese")
    english = data.get("english")
    if not chinese or not english:
        return jsonify({"message": "中文名称和英文名称均为必填项"}), 400

    # 读取现有 emotions.json（如果存在）
    try:
        if os.path.exists("emotions.json"):
            with open("emotions.json", "r", encoding="utf-8") as f:
                emotions = json.load(f)
        else:
            emotions = {}
    except Exception as e:
        emotions = {}

    # 添加新的分类映射
    emotions[chinese] = english

    try:
        with open("emotions.json", "w", encoding="utf-8") as f:
            json.dump(emotions, f, ensure_ascii=False, indent=4)
    except Exception as e:
        return jsonify({"message": f"更新 emotions.json 失败: {str(e)}"}), 500

    # 创建对应的表情包目录（以英文名称作为文件夹名）
    from .models import BASE_DIR

    category_path = os.path.join(BASE_DIR, english)
    if not os.path.exists(category_path):
        os.makedirs(category_path)

    return jsonify({"message": "Category added successfully"}), 201


# --- 图床相关 API ---


# 同步表情包目录到图床
@api.route("/sync_memes", methods=["POST"])
def sync_memes():
    memes_dir = "./memes"  # 设定表情包的本地目录
    try:
        result = image_host.sync_memes_to_host(memes_dir)
        return jsonify(result)
    except Exception as e:
        return jsonify({"message": f"同步表情包失败: {str(e)}"}), 500


# 上传单个文件到图床
@api.route("/upload", methods=["POST"])
def upload_to_host():
    category = request.form.get("category")
    if not category:
        return jsonify({"message": "Category is required"}), 400

    if "file" not in request.files:
        return jsonify({"message": "File is required"}), 400

    file = request.files["file"]
    temp_path = f"./temp_upload/{file.filename}"
    file.save(temp_path)

    try:
        upload_resp = image_host.upload_file(category, temp_path)
        return jsonify(upload_resp)
    except Exception as e:
        return jsonify({"message": f"上传文件到图床失败: {str(e)}"}), 500
