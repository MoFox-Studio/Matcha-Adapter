from maim_message import Router, RouteConfig, TargetConfig
from .config import global_config
from .logger import get_logger
from .send_handler import send_handler

logger = get_logger("mmc_com_layer")

route_config = RouteConfig(
    route_config={
        global_config.maibot_server.platform_name: TargetConfig(
            url=f"ws://{global_config.maibot_server.host}:{global_config.maibot_server.port}/ws",
            token=None,
        )
    }
)
router = Router(route_config,logger)


async def mmc_start_com():
    logger.info("正在连接MaiBot")
    router.register_class_handler(send_handler.handle_message)
    await router.run()


async def mmc_stop_com():
    await router.stop()
