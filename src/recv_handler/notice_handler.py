import asyncio
import json
import time

import websockets as Server
from maim_message import FormatInfo, UserInfo, GroupInfo, Seg, BaseMessageInfo, MessageBase

from src.config import global_config
from src.logger import get_logger
from src.utils import (
    get_group_info
)
from . import NoticeType, ACCEPT_FORMAT
from .message_sending import message_send_instance

notice_queue: asyncio.Queue[MessageBase] = asyncio.Queue(maxsize=100)
unsuccessful_notice_queue: asyncio.Queue[MessageBase] = asyncio.Queue(maxsize=3)


logger = get_logger("notice_handler")

class NoticeHandler:

    def __init__(self):
        self.server_connection: Server.ServerConnection = None

    async def set_server_connection(self, server_connection: Server.ServerConnection) -> None:
        """设置Matcha连接"""
        self.server_connection = server_connection

        while self.server_connection.state != Server.State.OPEN:
            await asyncio.sleep(0.5)

        asyncio.create_task(self.send_notice())



    async def handle_notice(self, raw_message: dict) -> None:
        notice_type = raw_message.get("notice_type")
        message_time: float = time.time()

        group_id = raw_message.get("group_id")
        user_id = raw_message.get("user_id")
        target_id = raw_message.get("target_id")

        handled_message: Seg = None
        user_info: UserInfo = None
        system_notice: bool = False

        match notice_type:
            case NoticeType.friend_recall:
                logger.info("好友撤回一条消息")
                logger.info(f"撤回消息ID：{raw_message.get('message_id')}, 撤回时间：{raw_message.get('time')}")
                logger.warning("暂时不支持撤回消息处理")
            case NoticeType.group_recall:
                logger.info("群内用户撤回一条消息")
                logger.info(f"撤回消息ID：{raw_message.get('message_id')}, 撤回时间：{raw_message.get('time')}")
                logger.warning("暂时不支持撤回消息处理")
            case NoticeType.notify:
                sub_type = raw_message.get("sub_type")
                match sub_type:
                    case _:
                        logger.warning(f"不支持的notify类型: {notice_type}.{sub_type}")
            case _:
                logger.warning(f"不支持的notice类型: {notice_type}")
                return None
        if not handled_message or not user_info:
            logger.warning("notice处理失败或不支持")
            return None

        group_info: GroupInfo = None
        if group_id:
            fetched_group_info = await get_group_info(self.server_connection, group_id)
            group_name: str = None
            if fetched_group_info:
                group_name = fetched_group_info.get("group_name")
            else:
                logger.warning("无法获取notice消息所在群的名称")
            group_info = GroupInfo(
                platform=global_config.maibot_server.platform_name,
                group_id=group_id,
                group_name=group_name,
            )

        message_info: BaseMessageInfo = BaseMessageInfo(
            platform=global_config.maibot_server.platform_name,
            message_id="notice",
            time=message_time,
            user_info=user_info,
            group_info=group_info,
            template_info=None,
            format_info=FormatInfo(
                content_format=["text", "notify"],
                accept_format=ACCEPT_FORMAT,
            ),
            additional_config={"target_id": target_id},  # 在这里塞了一个target_id，方便mmc那边知道被戳的人是谁
        )

        message_base: MessageBase = MessageBase(
            message_info=message_info,
            message_segment=handled_message,
            raw_message=json.dumps(raw_message),
        )

        if system_notice:
            await self.put_notice(message_base)
        else:
            logger.info("发送到Maibot处理通知信息")
            await message_send_instance.message_send(message_base)


    async def put_notice(self, message_base: MessageBase) -> None:
        """
        将处理后的通知消息放入通知队列
        """
        if notice_queue.full() or unsuccessful_notice_queue.full():
            logger.warning("通知队列已满，可能是多次发送失败，消息丢弃")
        else:
            await notice_queue.put(message_base)

    async def send_notice(self) -> None:
        """
        发送通知消息到Matcha
        """
        while True:
            if not unsuccessful_notice_queue.empty():
                to_be_send: MessageBase = await unsuccessful_notice_queue.get()
                try:
                    send_status = await message_send_instance.message_send(to_be_send)
                    if send_status:
                        unsuccessful_notice_queue.task_done()
                    else:
                        await unsuccessful_notice_queue.put(to_be_send)
                except Exception as e:
                    logger.error(f"发送通知消息失败: {str(e)}")
                    await unsuccessful_notice_queue.put(to_be_send)
                await asyncio.sleep(1)
                continue
            to_be_send: MessageBase = await notice_queue.get()
            try:
                send_status = await message_send_instance.message_send(to_be_send)
                if send_status:
                    notice_queue.task_done()
                else:
                    await unsuccessful_notice_queue.put(to_be_send)
            except Exception as e:
                logger.error(f"发送通知消息失败: {str(e)}")
                await unsuccessful_notice_queue.put(to_be_send)
            await asyncio.sleep(1)


notice_handler = NoticeHandler()
