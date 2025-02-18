from asyncio import wait
import os
import random
import string
from flask import (
    Flask,
    render_template,
    send_from_directory,
    request,
    redirect,
    url_for,
    session,
)
from backend.api import api

app = Flask(__name__)

# 注册API蓝图
app.register_blueprint(api, url_prefix="/api")

MEMES_DIR = "./memes"


# 生成随机秘钥的函数（用于登录验证）
def generate_secret_key(length=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


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
        return "File not found", 404


# 封装启动服务器的函数，每次启动时生成新秘钥
def start_server():
    global SERVER_LOGIN_KEY
    SERVER_LOGIN_KEY = generate_secret_key(8)
    print("当前秘钥为:", SERVER_LOGIN_KEY)
    # 设置 session 加密秘钥（每次启动时随机生成）
    app.secret_key = os.urandom(16)
    app.run(debug=True)


# 封装关闭服务器的函数（需要在请求上下文中调用）
def shutdown_server():
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        raise RuntimeError("无法关闭服务器：不是在 Werkzeug 环境中运行？")
    func()


if __name__ == "__main__":
    start_server()
