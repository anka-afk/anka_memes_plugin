from asyncio import wait
import os
import threading
import requests
from flask import (
    Flask,
    render_template,
    send_from_directory,
    request,
    redirect,
    url_for,
    session,
)
from .backend.api import api
from .utils import generate_secret_key

app = Flask(__name__)

# 注册API蓝图
app.register_blueprint(api, url_prefix="/api")

MEMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memes")


# 全局变量，用于保存当前的登录秘钥
SERVER_LOGIN_KEY = None


# 在每个请求前检查是否已认证，除登录页面和静态资源外都需要先登录
@app.before_request
def require_login():
    # 允许的 endpoint（静态文件和登录页不需要认证）
    allowed_endpoints = ["login", "static"]
    if request.endpoint not in allowed_endpoints and not session.get("authenticated"):
        return redirect(url_for("login"))


# 登录验证页面
@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return render_template("index.html")
    error = None
    if request.method == "POST":
        key = request.form.get("key")
        if key == SERVER_LOGIN_KEY:
            session["authenticated"] = True
            return redirect(url_for("login"))
        else:
            error = "秘钥错误，请重试。"
    return render_template("login.html", error=error)


# 静态资源
@app.route("/memes/<category>/<filename>")
def serve_emoji(category, filename):
    category_path = os.path.join(MEMES_DIR, category)
    if os.path.exists(os.path.join(category_path, filename)):
        return send_from_directory(category_path, filename)
    else:
        return "File not found" + os.path.join(category_path, filename), 404


@app.route("/shutdown_api", methods=["POST"])
def shutdown_api():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("无法关闭服务器：不是在 Werkzeug 环境中运行？")
    func()
    return "Server shutting down..."


# 封装启动服务器的函数，每次启动时生成新秘钥
def start_server(config=None):
    global SERVER_LOGIN_KEY
    SERVER_LOGIN_KEY = generate_secret_key(8)
    print("当前秘钥为:", SERVER_LOGIN_KEY)
    # 设置 session 加密秘钥（每次启动时随机生成）
    app.secret_key = os.urandom(16)
    # 如果传入了配置，则保存到 Flask app 的配置中
    if config is not None:
        app.config["PLUGIN_CONFIG"] = config
    # 读取端口号设置，默认为 5000
    port = 5000
    if config is not None:
        port = config.get("webui_port", 5000)
    # 启动服务器，使用配置中指定的端口号
    threading.Thread(
        target=lambda: app.run(
            debug=True, host="0.0.0.0", use_reloader=False, port=port
        )
    ).start()
    return SERVER_LOGIN_KEY


# 封装关闭服务器的函数
def shutdown_server():
    try:
        port = 5000
        plugin_config = app.config.get("PLUGIN_CONFIG", {})
        port = plugin_config.get("webui_port", 5000)
        # 服务器运行在指定的端口上
        requests.post(f"http://0.0.0.0:{port}/shutdown_api")
    except Exception as e:
        print("关闭服务器时出错:", e)


if __name__ == "__main__":
    start_server()
