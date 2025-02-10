import re
import os
import random
import logging
import json
import time

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import LLMResponse
from astrbot.api.message_components import *
from astrbot.api.event.filter import EventMessageType
from openai.types.chat.chat_completion import ChatCompletion
from astrbot.api.all import *

@register("mccloud_meme_sender", "MC云-小馒头", "识别AI回复中的表情并发送对应表情包", "1.0")
class MemeSender(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.found_emotions = []  # 存储找到的表情
        self.upload_states = {}  # 存储上传状态：{user_session: {"category": str, "expire_time": float}}

        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.meme_path = os.path.join(current_dir, "memes")

        self.emotion_map = {
            "生气": "angry",
            "开心": "happy",
            "悲伤": "sad",
            "惊讶": "surprised",
            "疑惑": "confused",
            "色色": "color",
            "色": "color",
            "死机": "cpu",
            "笨蛋": "fool",
            "给钱": "givemoney",
            "喜欢": "like",
            "看": "see",
            "害羞": "shy",
            "下班": "work",
            "剪刀": "scissors",
            "不回我": "reply",
            "喵": "meow",
            "八嘎": "baka",
            "早": "morning",
            "睡觉": "sleep",
            "唉": "sigh",
        }
        # 设置日志
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

        # 检查表情包目录
        self._check_meme_directories()

    @filter.command("查看表情包")
    async def list_emotions(self, event: AstrMessageEvent):
        """查看所有可用表情包类别"""
        categories = "\n".join([f"- {emotion}" for emotion in self.emotion_map.keys()])
        yield event.plain_result(f"当前支持的表情包类别：\n{categories}")

    @filter.command("上传表情包")
    async def upload_meme(self, event: AstrMessageEvent, category: str = None):
        """上传表情包到指定类别"""
        if not category:
            yield event.plain_result("请指定要上传的表情包类别，格式：/上传表情包 [类别名称]")
            return

        if category not in self.emotion_map:
            yield event.plain_result(f"无效的表情包类别：{category}\n使用/查看表情包查看可用类别")
            return

        user_key = f"{event.session_id}_{event.get_sender_id()}"
        self.upload_states[user_key] = {
            "category": category,
            "expire_time": time.time() + 30
        }
        yield event.plain_result(f"请于30秒内发送要添加到【{category}】类别的图片（支持多图）")

    @filter.event_message_type(filter.EventMessageType.ALL) 
    async def handle_upload_image(self, event: AstrMessageEvent):
        """处理图片上传"""
        user_key = f"{event.session_id}_{event.get_sender_id()}"
        state = self.upload_states.get(user_key)
        
        if not state or time.time() > state["expire_time"]:
            if state:
                del self.upload_states[user_key]
            return

        # 获取消息中的图片
        images = [c for c in event.message_obj.message if isinstance(c, Image)]
        if not images:
            yield event.plain_result("未检测到图片，请重新发送指令")
            return

        # 处理图片保存
        category = state["category"]
        saved_count = 0
        target_dir = os.path.join(self.meme_path, self.emotion_map[category])
        os.makedirs(target_dir, exist_ok=True)

        for img in images:
            try:
                # 处理不同来源的图片
                if img.path and os.path.exists(img.path):  # 本地图片
                    filename = f"{int(time.time())}_{os.path.basename(img.path)}"
                    dest = os.path.join(target_dir, filename)
                    shutil.copy(img.path, dest)
                    saved_count += 1
                elif img.url:  # 网络图片
                    async with aiohttp.ClientSession() as session:
                        async with session.get(img.url) as resp:
                            if resp.status == 200:
                                ext = os.path.splitext(img.url)[1] or ".jpg"
                                filename = f"{int(time.time())}_{len(os.listdir(target_dir))}{ext}"
                                dest = os.path.join(target_dir, filename)
                                
                                with open(dest, "wb") as f:
                                    while True:
                                        chunk = await resp.content.read(1024)
                                        if not chunk:
                                            break
                                        f.write(chunk)
                                saved_count += 1
                            else:
                                self.logger.error(f"下载图片失败：{resp.status}")
                else:
                    self.logger.warning("无法识别的图片格式")
            except Exception as e:
                self.logger.error(f"保存图片失败：{str(e)}")
                continue

        # 清理状态并返回结果
        del self.upload_states[user_key]
        result_msg = f"成功保存 {saved_count}/{len(images)} 张图片到【{category}】类别"
        if saved_count < len(images):
            result_msg += "\n部分图片保存失败，请检查格式（支持jpg/png/gif）"
        yield event.plain_result(result_msg)

    async def reload_emotions(self):
        """动态加载表情配置"""
        config_path = os.path.join(self.meme_path, "emotions.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.emotion_map.update(json.load(f))

    def _check_meme_directories(self):
        """检查表情包目录是否存在并且包含图片"""
        self.logger.info(f"表情包根目录: {self.meme_path}")
        if not os.path.exists(self.meme_path):
            self.logger.error(f"表情包根目录不存在: {self.meme_path}")
            return

        for emotion in self.emotion_map.values():
            emotion_path = os.path.join(self.meme_path, emotion)
            if not os.path.exists(emotion_path):
                self.logger.error(f"表情目录不存在: {emotion_path}")
                continue

            memes = [f for f in os.listdir(emotion_path) if f.endswith(('.jpg', '.png', '.gif'))]
            if not memes:
                self.logger.error(f"表情目录为空: {emotion_path}")
            else:
                self.logger.info(f"表情目录 {emotion} 包含 {len(memes)} 个图片")

    @filter.on_llm_response(priority=90)
    async def resp(self, event: AstrMessageEvent, response: LLMResponse):
        """处理 LLM 响应，识别表情"""
        if not response or not response.completion_text:
            return

        text = response.completion_text
        self.found_emotions = []  # 重置表情列表

        # 定义表情正则模式
        patterns = [
            r'\[([^\]]+)\]',  # [生气]
            r'\(([^)]+)\)',   # (生气)
            r'（([^）]+)）'    # （生气）
        ]

        clean_text = text

        # 查找所有表情标记
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                emotion = match.group(1)
                if emotion in self.emotion_map:
                    self.found_emotions.append(emotion)
                    clean_text = clean_text.replace(match.group(0), '')

        # 限制表情包数量
        self.found_emotions = list(dict.fromkeys(self.found_emotions))[:2]  # 去重并限制最多2个

        if self.found_emotions:
            # 更新回复文本(移除表情标记)
            response.completion_text = clean_text.strip()

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        """在消息发送前处理表情"""
        if not self.found_emotions:
            return

        result = event.get_result()
        if not result:
            return

        try:
            # 创建新的消息链
            chains = []

            # 添加原始文本消息链
            original_chain = result.chain
            if original_chain:
                if isinstance(original_chain, str):
                    chains.append(Plain(original_chain))
                elif isinstance(original_chain, MessageChain):
                    chains.extend(original_chain)
                elif isinstance(original_chain, list):
                    chains.extend(original_chain)
                else:
                    self.logger.warning(f"未知的消息链类型: {type(original_chain)}")

            # 添加表情包
            for emotion in self.found_emotions:
                emotion_en = self.emotion_map.get(emotion)
                if not emotion_en:
                    continue

                emotion_path = os.path.join(self.meme_path, emotion_en)
                if os.path.exists(emotion_path):
                    memes = [f for f in os.listdir(emotion_path) if f.endswith(('.jpg', '.png', '.gif'))]
                    try:
                        meme = random.choice(memes)
                    except IndexError:
                        self.logger.warning(f"表情目录为空: {emotion_path}")
                        continue

                    meme_file = os.path.join(emotion_path, meme)

                    # 使用正确的方式添加图片到消息链
                    chains.append(Image.fromFileSystem(meme_file))

            # 使用 make_result() 构建结果
            result = event.make_result()
            for component in chains:
                if isinstance(component, Plain):
                    result = result.message(component.text)
                elif isinstance(component, Image):
                    result = result.file_image(component.path)

            # 设置结果
            event.set_result(result)

        except Exception as e:
            self.logger.error(f"处理表情失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())

        # 清空表情列表
        self.found_emotions = []

    @filter.after_message_sent()
    async def after_message_sent(self, event: AstrMessageEvent):
        """消息发送后的清理工作"""
        self.found_emotions = []  # 确保清空表情列表
