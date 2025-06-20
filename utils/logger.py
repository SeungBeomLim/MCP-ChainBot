# utils/logger.py

import logging

logger = logging.getLogger("mcp_chainbot")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)
