import time
from typing import List, Dict

import websockets as Server
from maim_message import (
    UserInfo,
    GroupInfo,
    Seg,
    BaseMessageInfo,
    MessageBase,
    FormatInfo,
)

from src.config import global_config
from src.logger import get_logger
from src.utils import (
    get_group_info,
    get_image_base64,
    get_message_detail,
)
from . import RealMessageType, MessageType, ACCEPT_FORMAT
from .message_sending import message_send_instance


logger = get_logger("message_handler")

class MessageHandler:
    def __init__(self):
        self.server_connection: Server.ServerConnection = None
        self.bot_id_list: Dict[int, bool] = {}

    async def set_server_connection(self, server_connection: Server.ServerConnection) -> None:
        """设置Matcha连接"""
        self.server_connection = server_connection


    async def handle_raw_message(self, raw_message: dict) -> None:
        # sourcery skip: low-code-quality, remove-unreachable-code
        """
        从Matcha接受的原始消息处理

        Parameters:
            raw_message: dict: 原始消息
        """
        message_type: str = raw_message.get("message_type")
        message_id: int = raw_message.get("message_id")
        message_time: float = time.time()

        format_info: FormatInfo = FormatInfo(
            content_format=["text", "image", "emoji", "voice"],
            accept_format=ACCEPT_FORMAT,
        )  # 格式化信息
        if message_type == MessageType.private:
            sub_type = raw_message.get("sub_type")
            if sub_type == MessageType.Private.friend:
                sender_info: dict = raw_message.get("sender")

                # 发送者用户信息
                user_info: UserInfo = UserInfo(
                    platform=global_config.maibot_server.platform_name,
                    user_id=sender_info.get("user_id"),
                    user_nickname=sender_info.get("nickname"),
                    user_cardname=sender_info.get("card"),
                )

                # 不存在群信息
                group_info: GroupInfo = None
            elif sub_type == MessageType.Private.group:
                #TODO: 处理群临时消息
                logger.warning("群临时消息类型不支持")
                return None

            else:
                logger.warning(f"私聊消息类型 {sub_type} 不支持")
                return None
        elif message_type == MessageType.group:
            sub_type = raw_message.get("sub_type")
            if sub_type == MessageType.Group.normal:
                sender_info: dict = raw_message.get("sender")


                # 发送者用户信息
                user_info: UserInfo = UserInfo(
                    platform=global_config.maibot_server.platform_name,
                    user_id=sender_info.get("user_id"),
                    user_nickname=sender_info.get("nickname"),
                    user_cardname=sender_info.get("card"),
                )

                fetched_group_info = await get_group_info(self.server_connection, raw_message.get("group_id"))
                group_name: str = None
                if fetched_group_info:
                    group_name = fetched_group_info.get("group_name")

                group_info: GroupInfo = GroupInfo(
                    platform=global_config.maibot_server.platform_name,
                    group_id=raw_message.get("group_id"),
                    group_name=group_name,
                )

            else:
                logger.warning(f"群聊消息类型 {sub_type} 不支持")
                return None

        additional_config: dict = {}

        # 消息信息
        message_info: BaseMessageInfo = BaseMessageInfo(
            platform=global_config.maibot_server.platform_name,
            message_id=message_id,
            time=message_time,
            user_info=user_info,
            group_info=group_info,
            format_info=format_info,
            additional_config=additional_config,
        )

        # 处理实际信息
        if not raw_message.get("message"):
            logger.warning("原始消息内容为空")
            return None

        # 获取Seg列表
        seg_message: List[Seg] = await self.handle_real_message(raw_message)
        if not seg_message:
            logger.warning("处理后消息内容为空")
            return None
        submit_seg: Seg = Seg(
            type="seglist",
            data=seg_message,
        )
        # MessageBase创建
        message_base: MessageBase = MessageBase(
            message_info=message_info,
            message_segment=submit_seg,
            raw_message=raw_message.get("raw_message"),
        )

        logger.info("发送到Maibot处理信息")
        await message_send_instance.message_send(message_base)

    async def handle_real_message(self, raw_message: dict, in_reply: bool = False) -> List[Seg] | None:
        # sourcery skip: low-code-quality
        """
        处理实际消息
        Parameters:
            real_message: dict: 实际消息
        Returns:
            seg_message: list[Seg]: 处理后的消息段列表
        """
        real_message: list = raw_message.get("message")
        if not real_message:
            return None
        seg_message: List[Seg] = []
        for sub_message in real_message:
            sub_message: dict
            sub_message_type = sub_message.get("type")
            match sub_message_type:
                case RealMessageType.text:
                    ret_seg = await self.handle_text_message(sub_message)
                    if ret_seg:
                        seg_message.append(ret_seg)
                    else:
                        logger.warning("text处理失败")
                case RealMessageType.reply:
                    if not in_reply:
                        ret_seg = await self.handle_reply_message(sub_message)
                        if ret_seg:
                            seg_message += ret_seg
                        else:
                            logger.warning("reply处理失败")
                case RealMessageType.image:
                    ret_seg = await self.handle_image_message(sub_message)
                    if ret_seg:
                        seg_message.append(ret_seg)
                    else:
                        logger.warning("image处理失败")
                case RealMessageType.video:
                    logger.warning("不支持视频解析")
                case RealMessageType.node:
                    logger.warning("不支持转发消息节点解析")
                case _:
                    logger.warning(f"未知消息类型: {sub_message_type}")
        return seg_message

    @staticmethod
    async def handle_text_message(raw_message: dict) -> Seg:
        """
        处理纯文本信息
        Parameters:
            raw_message: dict: 原始消息
        Returns:
            seg_data: Seg: 处理后的消息段
        """
        message_data: dict = raw_message.get("data")
        plain_text: str = message_data.get("text")
        return Seg(type="text", data=plain_text)


    @staticmethod
    async def handle_image_message(raw_message: dict) -> Seg | None:
        """
        处理图片消息与表情包消息
        Parameters:
            raw_message: dict: 原始消息
        Returns:
            seg_data: Seg: 处理后的消息段
        """
        message_data: dict = raw_message.get("data")
        image_sub_type = message_data.get("sub_type")
        try:
            image_base64 = await get_image_base64(message_data.get("url"))
        except Exception as e:
            logger.error(f"图片消息处理失败: {str(e)}")
            return None
        if image_sub_type == 0:
            """这部分认为是图片"""
            return Seg(type="image", data=image_base64)
        elif image_sub_type not in [4, 9]:
            """这部分认为是表情包"""
            return Seg(type="emoji", data=image_base64)
        else:
            logger.warning(f"不支持的图片子类型：{image_sub_type}")
            return None

    async def handle_reply_message(self, raw_message: dict) -> List[Seg] | None:
        # sourcery skip: move-assign-in-block, use-named-expression
        """
        处理回复消息

        """
        raw_message_data: dict = raw_message.get("data")
        message_id: int = None
        if raw_message_data:
            message_id = raw_message_data.get("id")
        else:
            return None
        message_detail: dict = await get_message_detail(self.server_connection, message_id)
        if not message_detail:
            logger.warning("获取被引用的消息详情失败")
            return None
        reply_message = await self.handle_real_message(message_detail, in_reply=True)
        if reply_message is None:
            reply_message = "(获取发言内容失败)"
        sender_info: dict = message_detail.get("sender")
        sender_nickname: str = sender_info.get("nickname")
        sender_id: str = sender_info.get("user_id")
        seg_message: List[Seg] = []
        if not sender_nickname:
            logger.warning("无法获取被引用的人的昵称，返回默认值")
            seg_message.append(Seg(type="text", data="[回复 未知用户："))
        else:
            seg_message.append(Seg(type="text", data=f"[回复<{sender_nickname}:{sender_id}>："))
        seg_message += reply_message
        seg_message.append(Seg(type="text", data="]，说："))
        return seg_message

    async def _recursive_parse_image_seg(self, seg_data: Seg, to_image: bool) -> Seg:
        # sourcery skip: merge-else-if-into-elif
        if to_image:
            if seg_data.type == "seglist":
                new_seg_list = []
                for i_seg in seg_data.data:
                    parsed_seg = await self._recursive_parse_image_seg(i_seg, to_image)
                    new_seg_list.append(parsed_seg)
                return Seg(type="seglist", data=new_seg_list)
            elif seg_data.type == "image":
                image_url = seg_data.data
                try:
                    encoded_image = await get_image_base64(image_url)
                except Exception as e:
                    logger.error(f"图片处理失败: {str(e)}")
                    return Seg(type="text", data="[图片]")
                return Seg(type="image", data=encoded_image)
            elif seg_data.type == "emoji":
                image_url = seg_data.data
                try:
                    encoded_image = await get_image_base64(image_url)
                except Exception as e:
                    logger.error(f"图片处理失败: {str(e)}")
                    return Seg(type="text", data="[表情包]")
                return Seg(type="emoji", data=encoded_image)
            else:
                logger.trace(f"不处理类型: {seg_data.type}")
                return seg_data
        else:
            if seg_data.type == "seglist":
                new_seg_list = []
                for i_seg in seg_data.data:
                    parsed_seg = await self._recursive_parse_image_seg(i_seg, to_image)
                    new_seg_list.append(parsed_seg)
                return Seg(type="seglist", data=new_seg_list)
            elif seg_data.type == "image":
                return Seg(type="text", data="[图片]")
            elif seg_data.type == "emoji":
                return Seg(type="text", data="[动画表情]")
            else:
                logger.trace(f"不处理类型: {seg_data.type}")
                return seg_data


message_handler = MessageHandler()
