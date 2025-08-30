#!/usr/bin/env python3
"""Matcha-Adapter项目的主入口点"""

if __name__ == "__main__":
    import sys
    import os
    import asyncio
    from pathlib import Path
    
    # 添加当前目录到Python路径，这样可以识别src包
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    # 导入main模块
    import main
    
    # 手动执行main函数，模拟main.py的if __name__ == "__main__"行为
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main.main())
    except KeyboardInterrupt:
        from src.logger import get_logger
        logger = get_logger("main")
        logger.warning("收到中断信号，正在优雅关闭...")
        loop.run_until_complete(main.graceful_shutdown())
    except Exception as e:
        from src.logger import get_logger
        logger = get_logger("main")
        logger.exception(f"主程序异常: {str(e)}")
        sys.exit(1)
    finally:
        if loop and not loop.is_closed():
            loop.close()
        sys.exit(0)
