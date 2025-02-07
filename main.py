import re
import os
import random
import logging
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import LLMResponse
from astrbot.api.message_components import *
from openai.types.chat.chat_completion import ChatCompletion
from astrbot.api.all import *

@register("mccloud_meme_sender", "MC云-小馒头", "识别AI回复中的表情并发送对应表情包", "1.0.0")
class MemeSender(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.found_emotions = []  # 存储找到的表情
        
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
                    if memes:
                        meme = random.choice(memes)
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
