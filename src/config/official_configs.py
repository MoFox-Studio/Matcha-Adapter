from dataclasses import dataclass, field
from typing import Literal

from src.config.config_base import ConfigBase

"""
须知：
1. 本文件中记录了所有的配置项
2. 所有新增的class都需要继承自ConfigBase
3. 所有新增的class都应在config.py中的Config类中添加字段
4. 对于新增的字段，若为可选项，则应在其后添加field()并设置default_factory或default
"""

ADAPTER_PLATFORM = "matcha"


@dataclass
class MatchaServerConfig(ConfigBase):
    host: str = "localhost"
    """Matcha服务端的主机地址"""

    port: int = 8095
    """Matcha服务端的端口号"""

    heartbeat_interval: int = 30
    """Matcha心跳间隔时间，单位为秒"""


@dataclass
class MaiBotServerConfig(ConfigBase):
    platform_name: str = field(default=ADAPTER_PLATFORM, init=False)
    """平台名称"""

    host: str = "localhost"
    """MaiMCore的主机地址"""

    port: int = 8000
    """MaiMCore的端口号"""



@dataclass
class DebugConfig(ConfigBase):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    """日志级别，默认为INFO"""
