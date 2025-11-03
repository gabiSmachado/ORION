import asyncio
import json
from typing import Optional, Any
from contextlib import AsyncExitStack
import re
from openai import OpenAI
from mcp import ClientSession
from mcp.client.sse import sse_client
import logging 
import requests

class MCPClient:
    def __init__(self, api_key: str, logger: logging, rapp: str):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm = OpenAI(api_key=api_key)
        self.tools = []
        self.messages = []
        self.logger = logger
        self.rapp = rapp
        
    async def connect_to_server(self, server_url: str):
        """Connect to an MCP server.

        host/port/path are passed explicitly (taken from config in main) so we don't
        silently use a hard‑coded 127.0.0.1 which breaks in Kubernetes.
        """
        self.logger.info(f"Attempting to connect to server at {server_url}.")
        try:
            result = await self.exit_stack.enter_async_context(
                sse_client(server_url)
            )
            if isinstance(result, (tuple, list)):
                if len(result) < 2:
                    raise RuntimeError("streamablehttp_client returned fewer than 2 elements; cannot get read/write streams")
                self.read_stream, self.write_stream = result[0], result[1]
            else:
                self.read_stream = getattr(result, "read_stream", getattr(result, "read", None))
                self.write_stream = getattr(result, "write_stream", getattr(result, "write", None))
                if self.read_stream is None or self.write_stream is None:
                    raise RuntimeError("Unable to locate read/write streams on streamablehttp_client result")

            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.read_stream, self.write_stream)
            )

            try:
                await self.session.initialize()
            except asyncio.CancelledError as ce:
                # Provide clearer context for the common cancellation symptom the user saw
                raise RuntimeError(
                    "Initialization cancelled. This often means the server URL/path is incorrect or the server did not respond to the MCP initialize request."
                ) from ce
            except ConnectionResetError as cre:
                raise RuntimeError(
                    "Connection was reset by the server. Ensure the transport matches (use '/sse' for SSE servers) and that the server is running and reachable."
                ) from cre

            mcp_tools = await self.get_mcp_tools()
            self.tools = [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                }
                for tool in mcp_tools
            ]

            self.logger.info(
                f"Successfully connected to server. Available tools: {[tool['name'] for tool in self.tools]}"
            )
            # Inject a single system message with explicit tool usage guidance
            tool_help = []
            for t in self.tools:
                if t["name"] == "create_session":
                    schema = t.get("parameters", {})
                    # Provide a concise distilled schema reference
                    tool_help.append(
                        "create_session expects JSON like: {\n  \"body\": {\n    \"sliceQosProfile\": {\n      \"maxNumOfDevices\": <1-20>,\n      \"downStreamRatePerDevice\": {\"value\": <0-1024>, \"unit\": one of [bps,kbps,Mbps,Gbps,Tbps]},\n      \"upStreamRatePerDevice\": {\"value\": <0-1024>, \"unit\": ...},\n      \"downStreamDelayBudget\": {\"value\": <>=1, \"unit\": one of [Milliseconds,Seconds,...]},\n      \"upStreamDelayBudget\": {\"value\": <>=1, \"unit\": ...}\n    },\n    \"serviceTime\": {\"startDate\": RFC3339, \"endDate\": RFC3339?}, (optional)\n    \"serviceArea\": { optional description }\n  }\n}. Only call create_session when the user wants to create a new network slice. Do not omit the required 'body' wrapper."
                    )
                elif t["name"].startswith("get_"):
                    tool_help.append(f"{t['name']}: supply required parameters exactly as schema, NEVER empty. If asking for status of a specific session, require session_id UUID.")
                else:
                    tool_help.append(f"{t['name']}: follow its schema; do not hallucinate fields.")

            system_content = (
                "You are an assistant that MUST supply valid JSON arguments for tool calls. "
                "Never call a tool with empty braces if it has required fields. "
                "If the user gives a natural language slice description (e.g. Mbps, latency ms, number of devices), map it to the create_session tool. "
                "The default value for each field of the schema is always null."
                "Only one tool call per user intent unless the user explicitly requests multiple operations.\n\nTool guidance:\n" + "\n".join(tool_help)
            )
            # Initialize messages with the system prompt exactly once
            if not getattr(self, "messages", None):
                self.messages = []
            if not any(m.get("role") == "system" for m in self.messages):
                self.messages.insert(0, {"role": "system", "content": system_content})
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to server at {server_url}: {e}")
            raise

    async def get_mcp_tools(self):
        try:
            self.logger.info("Requesting MCP tools from the server.")
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            self.logger.error(f"Failed to get MCP tools: {str(e)}")
            raise Exception(f"Failed to get tools: {str(e)}")

    async def call_llm(self):
        """Call the LLM with the given query (kept for compatibility, prefer process_intent)."""
        try:
            return self.llm.responses.create(
                model="gpt-4o-mini",
                input=self.messages,
                tools=self.tools,
                # Encourage the model to leverage tools when appropriate
                instructions=(
                    "You have access to tools. If a tool can fulfill the user's request, "
                    "call the tool instead of replying with plain text. Use correct JSON arguments."
                ),
            )
        except Exception as e:
            self.logger.error(f"Failed to call LLM: {str(e)}")
            raise Exception(f"Failed to call LLM: {str(e)}")

    async def call_tool(self, tool_name: str, tool_args: dict):
        """Call a tool with the given name and arguments"""
        try:
            result = await self.session.call_tool(tool_name, tool_args)
            return result
        except Exception as e:
            self.logger.error(f"Failed to call tool: {str(e)}")
            raise Exception(f"Failed to call tool: {str(e)}")

    async def process_intent(self, intent: str):
        """Process an intent: prefer an LLM tool call; if none, return the LLM response.

        Returns the OpenAI Responses API response object. If a tool is invoked, also returns
        the follow-up response after providing the tool result back to the model.
        """
        try:
            self.logger.info(f"Processing intent: {intent}")
            user_intent = {"role": "user", "content": intent}
            self.messages.append(user_intent)
            
            response = self.llm.responses.create(
                model="gpt-4o-mini",
                input=self.messages,
                tools=self.tools,
                instructions=(
                    "You can call tools. If a tool can satisfy the user's request, "
                    "return a tool_call with the appropriate name and JSON arguments. "
                    "Only reply with plain text when no tool matches."
                )
            )
            
            for item in response.output:   
                if item.type == "function_call":
                    tool_name = item.name
                    tool_args = item.arguments
                    call_id = item.call_id

                    self.logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    try:
                        tool_result = await self.session.call_tool(
                            tool_name, json.loads(tool_args)
                        )
                        self.logger.info(f"Tool result: {tool_result}")
                    except Exception as e:
                        error_msg = f"Tool execution failed for {tool_name}: {str(e)}"
                        self.logger.error(error_msg)
                        raise Exception(error_msg)

                    tool_output = None
                    try:
                        if getattr(tool_result, 'content', None):
                            block = tool_result.content[0]
                            tool_output = getattr(block, 'text', None) or str(block)
                    except Exception:
                        tool_output = "<no text content>"
                        raise Exception(tool_output)

                    # Append a simple user message with the tool result so model can continue
                    self.messages.append({
                        "role": "user",
                        "content": f"Tool {tool_name} result (call_id={call_id}):\n{tool_output}"
                    })

                    result = json.loads(tool_output)["messageParsed"]
                    
                    try:
                        self.logger.info("Creating policy instance.")
                        policy = requests.post(f"{self.rapp}/create_policy", json=result, verify=False)
                        return policy
                    except Exception as e:
                        self.logger.error(f"Error creating policy instance.: {str(e)}")
                        raise
                    # final_response = self.llm.responses.create(
                    #     model="gpt-4o-mini",
                    #     input=self.messages,
                    #     tools=self.tools,
                    #     instructions="Use the tool result above to produce the final answer.",
                    # )
            self.logger.info("No tool_call found; returning text response.")
            return response
        except Exception as e:
            self.logger.error(f"Error processing intent: {e}")
            raise
         
    async def cleanup(self):
        """Clean up resources (close streams & session)."""
        try:
            self.logger.info("Shuting down MCP connection.")
            await self.exit_stack.aclose()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")