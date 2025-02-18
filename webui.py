import os
import multiprocessing
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


SERVER_LOGIN_KEY = None


@app.before_request
def require_login():
    allowed_endpoints = ["login", "static"]
    if request.endpoint not in allowed_endpoints and not session.get("authenticated"):
        return redirect(url_for("login"))


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


@app.route("/memes/<category>/<filename>")
def serve_emoji(category, filename):
    # 从 Flask 配置中获取 MEMES_DIR
    MEMES_DIR = app.config.get("MEMES_DIR", None)
    if MEMES_DIR is None:
        return "MEMES_DIR 未定义", 500

    category_path = os.path.join(MEMES_DIR, category)
    if os.path.exists(os.path.join(category_path, filename)):
        return send_from_directory(category_path, filename)
    else:
        return "File not found: " + os.path.join(category_path, filename), 404


@app.route("/shutdown_api", methods=["POST"])
def shutdown_api():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("无法关闭服务器：不是在 Werkzeug 环境中运行？")
    func()
    return "Server shutting down..."


def run_server(port):
    app.run(debug=True, host="0.0.0.0", use_reloader=False, port=port)


# 用于启动服务器的函数
def start_server(config=None):
    global SERVER_LOGIN_KEY
    SERVER_LOGIN_KEY = generate_secret_key(8)
    print("当前秘钥为:", SERVER_LOGIN_KEY)

    app.secret_key = os.urandom(16)

    if config is not None:
        app.config["PLUGIN_CONFIG"] = config

    # 计算绝对路径并存入配置
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    PLUGIN_CONFIG = app.config.get("PLUGIN_CONFIG", {})

    memes_path = PLUGIN_CONFIG.get("memes_path", "memes")
    if not os.path.isabs(memes_path):
        MEMES_DIR = os.path.abspath(os.path.join(_base_dir, memes_path))
    else:
        MEMES_DIR = memes_path

    # 将计算好的 MEMES_DIR 存储到 app.config 中
    app.config["MEMES_DIR"] = MEMES_DIR

    # 启动服务器
    port = config.get("webui_port", 5000) if config else 5000
    server_process = multiprocessing.Process(target=run_server, args=(port,))
    server_process.start()
    return SERVER_LOGIN_KEY, server_process


# 用于关闭服务器的函数
def shutdown_server(server_process):
    try:
        plugin_config = app.config.get("PLUGIN_CONFIG", {})
        port = plugin_config.get("webui_port", 5000)
        requests.post(f"http://127.0.0.1:{port}/shutdown_api")
        server_process.join(timeout=5)  # 等待进程退出
        if server_process.is_alive():
            server_process.terminate()
    except Exception as e:
        print("关闭服务器时出错:", e)
