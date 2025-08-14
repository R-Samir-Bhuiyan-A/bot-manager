# app/utils.py
import os
import time
import asyncio
from typing import AsyncGenerator

def assure_dir(path):
    os.makedirs(path, exist_ok=True)

# Async tail - works well with FastAPI websockets without blocking the loop
async def tail_f(path: str) -> AsyncGenerator[str, None]:
    print(f"Starting to tail file: {path}")  # Debug log
    while not os.path.exists(path):
        print(f"Waiting for file to exist: {path}")  # Debug log
        await asyncio.sleep(0.2)
    
    print(f"File exists, starting to read: {path}")  # Debug log
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, os.SEEK_END)
        buf = ""
        while True:
            chunk = f.read()
            if chunk:
                print(f"Read chunk of {len(chunk)} bytes")  # Debug log
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    yield line + "\n"
            else:
                await asyncio.sleep(0.2)
