import sys
import os
import yaml
import asyncio
from dotenv import load_dotenv
import streamlit as st
from chatbot import Chatbot
from utils.logger import get_logger

logger = get_logger("front-end", log_file="frontend.log", level=20, console_level=20)

load_dotenv()
CONFIG_FILE_PATH = 'config/config.yaml'

async def main():
    try:
        logger.info("Starting MCP Client Frontend.")

        host = None
        port = None

        # Prefer config file if present
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r') as f:
                raw_cfg = yaml.safe_load(f) or {}
                
                section = raw_cfg.get('mcp_client') or raw_cfg.get('api') or raw_cfg
                host = section.get('host') if isinstance(section, dict) else None
                port = section.get('port') if isinstance(section, dict) else None
        else:
            logger.warning(f"Config file not found at {CONFIG_FILE_PATH}; falling back to env vars.")

        # Fallback to env vars if needed
        host = host or os.getenv('API_HOST') or 'localhost'
        port = port or os.getenv('API_PORT') or '9100'

        client_url = f"http://{host}:{port}"
        logger.info(f"Connecting to {client_url}")
    except yaml.YAMLError as exc:
        logger.error(f"Error parsing configuration file: {exc}")
        sys.exit(1)
    
    if "server_connected" not in st.session_state:
        st.session_state["server_connected"] = False

    if "tools" not in st.session_state:
        st.session_state["tools"] = []
        
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    st.set_page_config(page_title="MCP Client", page_icon=":shark:")

    chatbot = Chatbot(client_url)
    await chatbot.render()


if __name__ == "__main__":
    asyncio.run(main())