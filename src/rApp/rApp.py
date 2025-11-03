import uvicorn
import json
import yaml
import sys
from pathlib import Path
from fastapi import FastAPI
from dotenv import load_dotenv
from utils.logger import get_logger
from tools import create_policy
from fastapi.responses import JSONResponse
import requests

logger = get_logger("rApp", log_file="rApp.log", level=20, console_level=20)

load_dotenv()

CONFIG_FILE_PATH = Path(__file__).parent / 'config' / 'config.yaml'

try:
    logger.info("Starting rApp")
    if not CONFIG_FILE_PATH.exists():
        raise FileNotFoundError(str(CONFIG_FILE_PATH))

    with CONFIG_FILE_PATH.open('r') as f:
        raw_cfg = yaml.safe_load(f) or {}

    PlmnId = raw_cfg.get('PlmnId', {})
    mcc = PlmnId.get('mcc')
    mnc = PlmnId.get('mnc')
    
    nonrtric = raw_cfg.get('nonrtric')
    ric_id = nonrtric.get('ric_id')
    service_id = nonrtric.get('service_id')
    policytype_id = nonrtric.get('policytype_id')
    url = nonrtric.get('base_url_pms')

    rapp = raw_cfg.get('rapp')
    host = rapp.get('host')
    port = rapp.get('port')
    
    logger.info(f"Loaded config from {CONFIG_FILE_PATH} (ric_id={ric_id})")

except FileNotFoundError:
    msg = f"Configuration file not found: {CONFIG_FILE_PATH} (cwd={Path.cwd()})"
    print(msg)
    logger.error(msg)
    sys.exit(1)
except yaml.YAMLError as exc:
    msg = f"Error parsing configuration file: {exc}"
    print(msg)
    logger.error(msg)
    sys.exit(1)


def create_instance(body):
    """Create a policy instance in the PMS."""

    headers = {"content-type": "application/json"}
    logger.info(f"Sending PUT request to {url} with body: {json.dumps(body, indent=2)}")

    try:
        resp = requests.put(url, json=body, headers=headers, verify=False)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.error(f"Failed to create policy. Error: {exc}")
        payload = {
            "status": "Policy creation failed",
            "code": 500,
            "message": f"Request error: {exc}",
        }
        return JSONResponse(status_code=500, content=payload)

    if resp.status_code != 200:
        logger.error(f"Policy creation failed with status {resp.status_code}: {resp.text}")
        payload = {
            "status": "Policy creation failed",
            "code": resp.status_code,
            "message": resp.text or "Unexpected response from PMS",
        }
        return JSONResponse(status_code=resp.status_code, content=payload)

    policy_id = body.get("policy_id")
    logger.info("Policy created successfully")
    payload = {
        "status": "Policy created successfully",
        "code": 200,
        "message": f"Policy created successfully (policy_id={policy_id})",
    }
    return JSONResponse(status_code=200, content=payload)
app = FastAPI()

@app.post("/create_policy")
async def read_root(body: dict):
    policy = create_policy(body, ric_id, mcc, mnc, service_id, policytype_id)
    instance = create_instance(policy)
    return instance

if __name__ == "__main__":
   uvicorn.run(app, host=host, port=port)