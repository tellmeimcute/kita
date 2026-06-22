


import logging
from core.config.base import BaseConfig

class _LogConfig(BaseConfig):
    log_level: str = "INFO"

def setup_logging():
    tmp_conf = _LogConfig()
    level = tmp_conf.log_level.upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )