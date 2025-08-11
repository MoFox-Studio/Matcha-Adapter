from enum import Enum


class CommandType(Enum):
    """命令类型"""

    GROUP_BAN = "set_group_ban"  # 禁言用户
    GROUP_WHOLE_BAN = "set_group_whole_ban"  # 群全体禁言
    GROUP_KICK = "set_group_kick"  # 踢出群聊
    SEND_POKE = "send_poke"  # 戳一戳
    DELETE_MSG = "delete_msg"  # 撤回消息
    AI_VOICE_SEND = "send_group_ai_record"  # 发送群AI语音

    def __str__(self) -> str:
        return self.value
