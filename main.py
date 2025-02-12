import re
import os
import random
import logging
import json
import time
import aiohttp
import aiofiles
import traceback
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import LLMResponse
from astrbot.api.message_components import *
from astrbot.api.event.filter import EventMessageType
from openai.types.chat.chat_completion import ChatCompletion
from astrbot.api.all import *


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

import os
import time
import random
import logging
import aiohttp
import aiofiles
import traceback
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import Image
from astrbot.api.event.filter import EventMessageType

@register("mccloud_meme_sender", "MC云-小馒头", "识别AI回复中的表情并发送对应表情包", "1.0")
class MemeSender(Star):
    def init(self, context: Context, config: dict = None):
        super().init(context)
        self.config = config or {}
        self.found_emotions = []  # 存储找到的表情
        self.upload_states = {}   # 存储上传状态：{user_session: {"category": str, "expire_time": float}}
    
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
    
        # 设置日志（强制设置级别为DEBUG）
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
    
        # 检查表情包目录
        self._check_meme_directories()

    def _get_extension_from_content_type(self, content_type: str) -> str:
        mapping = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp'
        }
        return mapping.get(content_type, '.jpg')

    # ... 其余代码 ...

    @filter.event_message_type(EventMessageType.ALL)
    async def handle_upload_image(self, event: AstrMessageEvent):
        """处理图片上传并输出详细调试信息"""
        user_key = f"{event.session_id}_{event.get_sender_id()}"
        self.logger.info(f"[handle_upload_image] 用户 key: {user_key}")

        # 如果该用户没有处于上传状态，则直接返回
        if user_key not in self.upload_states:
            self.logger.info(f"[handle_upload_image] 用户 {user_key} 未处于上传状态，忽略此消息。")
            return

        # 检查上传状态是否过期
        if time.time() > self.upload_states[user_key]["expire_time"]:
            self.logger.info(f"[handle_upload_image] 用户 {user_key} 的上传状态已过期。")
            del self.upload_states[user_key]
            yield event.plain_result("上传超时，请重新上传表情包。")
            return

        # 输出完整的消息链调试信息
        self.logger.info(f"[handle_upload_image] 完整的消息链: {event.message_obj.message}")
        images = []
        for i, comp in enumerate(event.message_obj.message):
            comp_type = type(comp)
            self.logger.info(f"[handle_upload_image] 消息组件 {i}: 类型: {comp_type}, 内容: {repr(comp)}")
            # 如果组件是 Image 类型，或者含有 file 属性，则认为是图片组件
            if isinstance(comp, Image):
                images.append(comp)
            elif hasattr(comp, "file"):
                self.logger.info(f"[handle_upload_image] 组件 {i} 有 file 属性: {comp.file}")
                images.append(comp)
            else:
                self.logger.info(f"[handle_upload_image] 组件 {i} 未匹配为图片组件。")

        self.logger.info(f"[handle_upload_image] 从消息中检测到 {len(images)} 个图片组件。")
        if not images:
            self.logger.info(f"[handle_upload_image] 消息中未检测到图片组件。")
            return

        # 从上传状态中获取用户指定的类别（upload_meme 指令中已校验类别合法性）
        category = self.upload_states[user_key]["category"]
        self.logger.info(f"[handle_upload_image] 用户 {user_key} 正在上传类别: {category}")
        category_en = self.emotion_map.get(category)
        if not category_en:
            self.logger.error(f"[handle_upload_image] 未知的表情包类别: {category}")
            yield event.plain_result("上传失败：未知的表情包类别。")
            del self.upload_states[user_key]
            return

        # 构造存储图片的目录（不存在则自动创建）
        save_dir = os.path.join(self.meme_path, category_en)
        if not os.path.exists(save_dir):
            self.logger.info(f"[handle_upload_image] 目录 {save_dir} 不存在，尝试创建。")
            os.makedirs(save_dir, exist_ok=True)
        else:
            self.logger.info(f"[handle_upload_image] 目录 {save_dir} 已存在。")

        uploaded_count = 0
        async with aiohttp.ClientSession() as session:
            for img in images:
                image_url = getattr(img, "file", None)
                self.logger.info(f"[handle_upload_image] 尝试下载图片: {image_url}")
                if not image_url:
                    self.logger.error(f"[handle_upload_image] 图片组件中未找到有效的 file 属性: {img}")
                    continue
                try:
                    async with session.get(image_url) as resp:
                        self.logger.info(f"[handle_upload_image] 收到响应, 状态码: {resp.status}, 响应头: {resp.headers}")
                        if resp.status != 200:
                            self.logger.error(f"[handle_upload_image] 下载图片失败: {image_url} 状态码: {resp.status}")
                            continue
                        content = await resp.read()
                        self.logger.info(f"[handle_upload_image] 下载成功，图片大小: {len(content)} 字节")
                        content_type = resp.headers.get("Content-Type", "")
                        extension = self._get_extension_from_content_type(content_type)
                        self.logger.info(f"[handle_upload_image] Content-Type: {content_type}，解析得到扩展名: {extension}")
                        filename = f"{int(time.time())}_{random.randint(1000,9999)}{extension}"
                        file_path = os.path.join(save_dir, filename)
                        self.logger.info(f"[handle_upload_image] 保存文件路径: {file_path}")
                        async with aiofiles.open(file_path, "wb") as f:
                            await f.write(content)
                        self.logger.info(f"[handle_upload_image] 成功保存图片至 {file_path}")
                        uploaded_count += 1
                except Exception as e:
                    self.logger.error(f"[handle_upload_image] 下载图片时发生异常: {str(e)}")
                    self.logger.error(traceback.format_exc())

        if uploaded_count:
            self.logger.info(f"[handle_upload_image] 用户 {user_key} 上传了 {uploaded_count} 张图片。")
            yield event.plain_result(f"成功上传 {uploaded_count} 张图片到【{category}】类别。")
        else:
            self.logger.warning(f"[handle_upload_image] 用户 {user_key} 未能上传任何图片。")
            yield event.plain_result("未能上传任何图片，请检查图片链接是否有效。")

        del self.upload_states[user_key]
        self.logger.info(f"[handle_upload_image] 清除用户 {user_key} 的上传状态。")




    def _get_extension_from_content_type(self, content_type: str) -> str:
        """根据 Content-Type 获取文件扩展名"""
        mapping = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp'
        }
        return mapping.get(content_type, '.jpg')


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
