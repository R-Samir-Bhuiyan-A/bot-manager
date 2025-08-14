# app/manager.py
import os
import json
import asyncio
from typing import Dict, Any
import tomli
import tomli_w

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .bots_manager import BotRegistry

app = FastAPI(title="Bot Manager")

# Ensure data directory and bots subdirectory exist
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
BOTS_DIR = os.path.join(DATA_DIR, "bots")
os.makedirs(BOTS_DIR, exist_ok=True)

reg = BotRegistry()

# Load manager settings
MANAGER_SETTINGS_PATH = os.path.join(DATA_DIR, "manager_settings.toml")
manager_settings = {}

def load_manager_settings():
    global manager_settings
    try:
        if os.path.exists(MANAGER_SETTINGS_PATH):
            with open(MANAGER_SETTINGS_PATH, "rb") as f:
                manager_settings = tomli.load(f)
        else:
            # Create default settings file
            default_settings = {
                "ui": {"theme": "dark", "refresh_interval": 2000},
                "logs": {"max_lines": 1000, "auto_scroll": True, "buffer_size": 8192},
                "web": {"host": "0.0.0.0", "port": 8080}
            }
            with open(MANAGER_SETTINGS_PATH, "wb") as f:
                tomli_w.dump(default_settings, f)
            manager_settings = default_settings
    except Exception as e:
        print(f"Error loading manager settings: {e}")
        manager_settings = {
            "ui": {"theme": "dark", "refresh_interval": 2000},
            "logs": {"max_lines": 1000, "auto_scroll": True, "buffer_size": 8192},
            "web": {"host": "0.0.0.0", "port": 8080}
        }

load_manager_settings()

# serve static UI
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")

@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse('<meta http-equiv="refresh" content="0; url=/ui/index.html">')

# API endpoint to get manager settings
@app.get("/api/manager/settings")
def get_manager_settings():
    return manager_settings

# API endpoint to update manager settings
@app.put("/api/manager/settings")
def update_manager_settings(payload: Dict[str, Any] = Body(...)):
    global manager_settings
    try:
        # Update settings
        for key, value in payload.items():
            if key in manager_settings:
                manager_settings[key].update(value)
            else:
                manager_settings[key] = value
        
        # Save settings to file
        with open(MANAGER_SETTINGS_PATH, "wb") as f:
            tomli_w.dump(manager_settings, f)
        
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------- Helpers --------
def infer_schema_from_toml(data: Any) -> dict:
    if isinstance(data, dict):
        return {"type":"object","properties":{k:infer_schema_from_toml(v) for k,v in data.items()}}
    if isinstance(data, bool): return {"type":"boolean"}
    if isinstance(data, int): return {"type":"integer"}
    if isinstance(data, float): return {"type":"number"}
    if isinstance(data, list):
        if all(isinstance(x, str) for x in data):
            return {"type":"array","items":{"type":"string"}}
        return {"type":"array","items":{"type":"any"}}
    return {"type":"string"}

def coerce(schema: dict, payload: Any) -> Any:
    t = schema.get("type")
    if t == "object":
        out = {}
        for k, sub in schema.get("properties", {}).items():
            if k in payload:
                out[k] = coerce(sub, payload[k])
        # Include any extra keys (be flexible)
        for k, v in payload.items():
            if k not in out:
                out[k] = v
        return out
    if t == "boolean":
        v = payload
        if isinstance(v, str): return v.lower() in ("true","1","yes","on")
        return bool(v)
    if t == "integer": return int(payload)
    if t == "number": return float(payload)
    if t == "array":
        v = payload
        if isinstance(v, str):
            return [x.strip() for x in v.splitlines() if x.strip()]
        if isinstance(v, list): return v
        return [v]
    return "" if payload is None else str(payload)

# ---------- REST: bots ----------
@app.get("/api/bots")
def list_bots():
    return reg.snapshot()

@app.post("/api/bots")
def create_bot(req: Dict[str, str] = Body(...)):
    name = req.get("name","Bot")
    bot_id = reg.create_from_template(name)
    return {"id": bot_id}

@app.delete("/api/bots/{bot_id}")
def delete_bot(bot_id: str):
    reg.delete(bot_id)
    return {"ok": True}

@app.post("/api/bots/{bot_id}/start")
def start_bot(bot_id: str):
    reg.start(bot_id)
    return {"ok": True}

@app.post("/api/bots/{bot_id}/stop")
def stop_bot(bot_id: str):
    reg.stop(bot_id)
    return {"ok": True}

@app.post("/api/bots/{bot_id}/restart")
def restart_bot(bot_id: str):
    reg.restart(bot_id)
    return {"ok": True}

# ---------- REST: config (dynamic) ----------
@app.get("/api/bots/{bot_id}/config")
def get_config(bot_id: str):
    cfg_path = reg.config_path(bot_id)
    data = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, "rb") as f:
            data = tomli.load(f)
    schema = infer_schema_from_toml(data if data else {"_":""})
    return {"config": data, "schema": schema}

@app.put("/api/bots/{bot_id}/config")
def put_config(bot_id: str, payload: Dict[str, Any] = Body(...)):
    cfg_path = reg.config_path(bot_id)
    current = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, "rb") as f:
            current = tomli.load(f)
    schema = infer_schema_from_toml(current if current else payload)
    coerced = coerce(schema, payload)

    with open(cfg_path, "wb") as f:
        tomli_w.dump(coerced, f)

    reg._apply_schedules(bot_id)
    return {"ok": True}

# ---------- Logs ----------
@app.get("/api/bots/{bot_id}/logs.txt", response_class=PlainTextResponse)
def read_log(bot_id: str):
    b = reg._get(bot_id)
    if not os.path.exists(b.logfile):
        return ""
    try:
        with open(b.logfile, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"LOG ERROR: {e}"

@app.get("/api/bots/{bot_id}/logs")
def download_log(bot_id: str):
    b = reg._get(bot_id)
    if not os.path.exists(b.logfile):
        return PlainTextResponse("", media_type="text/plain")
    return FileResponse(b.logfile, filename=f"{bot_id}.log")

# ---------- WS: status feed (lower frequency to avoid UI jank) ----------
status_clients = set()

@app.websocket("/ws/status")
async def ws_status(ws: WebSocket):
    await ws.accept()
    status_clients.add(ws)
    try:
        while True:
            await ws.send_text(json.dumps(reg.snapshot()))
            await asyncio.sleep(2.0)  # 2s — smoother and lighter
    except WebSocketDisconnect:
        status_clients.discard(ws)

# ---------- WS: live log tail ----------
from .utils import tail_f

@app.websocket("/ws/logs/{bot_id}")
async def ws_logs(ws: WebSocket, bot_id: str):
    print(f"WebSocket connection request for bot logs: {bot_id}")  # Debug log
    await ws.accept()
    print(f"WebSocket connection accepted for bot logs: {bot_id}")  # Debug log
    try:
        b = reg._get(bot_id)
        logfile_path = str(b.logfile)
        
        # Debug: Print the logfile path
        print(f"Attempting to tail log file: {logfile_path}")
        
        # Check if log file exists, if not, wait for it to be created
        max_wait_time = 30  # seconds
        wait_interval = 0.5  # seconds
        wait_count = 0
        
        while not os.path.exists(logfile_path) and wait_count < (max_wait_time / wait_interval):
            print(f"Waiting for log file to exist: {logfile_path}")  # Debug log
            await asyncio.sleep(wait_interval)
            wait_count += 1
        
        if not os.path.exists(logfile_path):
            error_msg = f"Log file not found at {logfile_path}. Bot may not be started yet."
            print(error_msg)
            await ws.send_text(error_msg)
            await asyncio.sleep(1)  # Give time for the message to be sent
            return
            
        # Debug: Print file exists
        print(f"Log file exists: {logfile_path}")
        
        async for line in tail_f(logfile_path):
            try:
                # Check if the WebSocket is still connected
                if hasattr(ws, 'client_state') and ws.client_state == "connected":
                    await ws.send_text(line.rstrip("\n"))
                elif hasattr(ws, 'application_state') and not ws.application_state.name == "DISCONNECTED":
                    await ws.send_text(line.rstrip("\n"))
                else:
                    print(f"WebSocket disconnected for bot {bot_id}")  # Debug log
                    break
            except Exception as e:
                # Client disconnected or other WebSocket error
                print(f"WebSocket send error for bot {bot_id}: {e}")  # Debug log
                break
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for bot {bot_id}")  # Debug log
        pass
    except Exception as e:
        error_msg = f"Error reading logs for bot {bot_id}: {str(e)}"
        print(error_msg)  # Log to server console
        try:
            await ws.send_text(error_msg)
        except:
            pass
    finally:
        try:
            if hasattr(ws, 'client_state') and ws.client_state == "connected":
                await ws.close()
            elif hasattr(ws, 'application_state') and not ws.application_state.name == "DISCONNECTED":
                await ws.close()
        except Exception as e:
            print(f"Error closing WebSocket for bot {bot_id}: {e}")  # Debug log
        print(f"WebSocket connection closed for bot {bot_id}")  # Debug log

# ---------- WS: manager logs ----------
import logging
import asyncio
from typing import Set

manager_log_clients: Set[WebSocket] = set()

# Custom handler to broadcast log messages to WebSocket clients
class WebSocketLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.clients = set()
        
    def emit(self, record):
        # Format the log record
        log_entry = self.format(record)
        
        # Send to all connected clients
        async def send_to_clients():
            disconnected_clients = set()
            for client in self.clients:
                try:
                    if hasattr(client, 'client_state') and client.client_state == "connected":
                        await client.send_text(log_entry)
                    elif not client.application_state.name == "DISCONNECTED":
                        await client.send_text(log_entry)
                    else:
                        disconnected_clients.add(client)
                except:
                    disconnected_clients.add(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.clients.discard(client)
                manager_log_clients.discard(client)
        
        # Run the async function
        try:
            asyncio.create_task(send_to_clients())
        except:
            pass

# Create and configure the log handler
ws_log_handler = WebSocketLogHandler()
ws_log_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
ws_log_handler.setFormatter(formatter)

# Add the handler to the root logger
logging.getLogger().addHandler(ws_log_handler)

@app.websocket("/ws/manager/logs")
async def ws_manager_logs(ws: WebSocket):
    await ws.accept()
    manager_log_clients.add(ws)
    ws_log_handler.clients.add(ws)
    
    try:
        await ws.send_text("Manager logs connection established.")
        
        # Keep connection alive
        while True:
            # Send a heartbeat every 30 seconds
            await ws.send_text(":heartbeat:")
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        pass
    finally:
        manager_log_clients.discard(ws)
        ws_log_handler.clients.discard(ws)
