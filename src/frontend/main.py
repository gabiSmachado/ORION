import sys
import os
import yaml
import asyncio
from dotenv import load_dotenv
import streamlit as st
from chatbot import Chatbot
from utils.logger import get_logger

load_dotenv()
CONFIG_FILE_PATH = 'config/config.yaml'

async def main():
    logger = get_logger("front-end", log_file="frontend.log", level=20, console_level=20)

    try:
        # Prefer config file if present
        with open(CONFIG_FILE_PATH, 'r') as f:
            raw_cfg = yaml.safe_load(f) or {}
            section = raw_cfg.get('mcp_client')
            host = section.get('host')
            port = section.get('port')

            client_url = "http://127.0.0.1:9100"
            #f"http://{host}:{port}"
            logger.info(f"Connecting to {client_url}")
    except FileNotFoundError:
        print(f"Configuration file not found: {CONFIG_FILE_PATH}")
        logger.info(f"Configuration file not found: {CONFIG_FILE_PATH}")
        sys.exit(1)
    
    except yaml.YAMLError as exc:
        logger.error(f"Error parsing configuration file: {exc}")
        sys.exit(1)
        
    chatbot = Chatbot(client_url, logger)
    await chatbot.render()


if __name__ == "__main__":
    asyncio.run(main())