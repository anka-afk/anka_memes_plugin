from abc import ABC, abstractmethod


class ImageHost(ABC):
    """
    图床接口，定义所有图床都必须实现的方法
    """

    @abstractmethod
    def create_space(self, space: str) -> dict:
        """创建图床空间"""
        pass

    @abstractmethod
    def upload_file(self, space: str, file_path: str) -> dict:
        """上传文件到指定空间"""
        pass

    @abstractmethod
    def sync_memes_to_host(self, memes_dir: str) -> dict:
        """同步本地表情包目录到图床"""
        pass
