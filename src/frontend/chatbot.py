import streamlit as st
import httpx
from typing import Dict, Any
import json
import logging 

class Chatbot:
    def __init__(self, api_url: str, logger: logging,):
        self.api_url = api_url
        self.logger = logger
        self.current_tool_call = {"name": None, "args": None}
        # Ensure chat history state exists before we try to render it
        self.messages = st.session_state.setdefault("messages", [])

    def display_message(self, message: Dict[str, Any]):
        # display user message
        if message["role"] == "user" and type(message["content"]) == str:
            st.chat_message("user").markdown(message["content"])

        # display tool result
        if message["role"] == "user" and type(message["content"]) == list:
            for content in message["content"]:
                if content["type"] == "tool_result":
                    with st.chat_message("assistant"):
                        st.write(f"Called tool: {self.current_tool_call['name']}:")
                        st.json(
                            {
                                "name": self.current_tool_call["name"],
                                "args": self.current_tool_call["args"],
                                "content": json.loads(content["content"][0]["text"]),
                            },
                            expanded=False,
                        )

        # display ai message
        if message["role"] == "assistant" and type(message["content"]) == str:
            st.chat_message("assistant").markdown(message["content"])

        # store current ai tool use
        if message["role"] == "assistant" and type(message["content"]) == list:
            for content in message["content"]:
                # ai tool use
                if content["type"] == "tool_use":
                    self.current_tool_call = {
                        "name": content["name"],
                        "args": content["input"],
                    }
 
    async def render(self):
        st.set_page_config(page_title="ORION", page_icon=":material/cell_tower:")
        st.title("ORION")
        st.subheader("Intent-Aware Orchestration in Open RAN for SLA-Driven Network Management")    

        # Display existing messages
        for message in self.messages:
            self.display_message(message)

        # Handle new intent
        intent = st.chat_input("Enter your intent here")
        if intent:
            self.logger.info("Submitting intent: %s", intent)
            st.write(f"{intent}")
            async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
                try:
                    response = await client.post(
                        f"{self.api_url}/intent",
                        json={"intent": intent},
                        headers={"Content-Type": "application/json"},
                    )
                    st.write(f"Processing Intent ...")
                    
                    self.logger.info(
                        "Received response (status %s): %s",
                        getattr(response, "status_code", "?"),
                        response.text,
                    )

                    # Try to parse JSON, fallback to plain text
                    try:
                        payload = response.json()
                        # If a message field exists, show it directly; else show JSON
                        if isinstance(payload, dict):
                            if "message" in payload:
                                st.write(payload["message"])
                            else:
                                st.json(payload, expanded=False)
                        else:
                            st.write(str(payload))
                    except (ValueError, json.JSONDecodeError):
                        # Not JSON; display the raw text content
                        st.write(response.text)

                except Exception as e:
                    self.logger.exception("Error processing intent", exc_info=e)
                    st.error(
                        "Frontend: Error processing intent: "
                        f"{e} (URL: {self.api_url}/intent). "
                        "Check that the MCP Client API is running and reachable."
                    )