import logging

try:
    from loguru import logger
except ImportError:
    logger = logging.getLogger("hermes_codex_plugin")
