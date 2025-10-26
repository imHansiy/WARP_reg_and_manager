# -*- coding: utf-8 -*-
"""
WebSocket bridge between extension and Python backend.
Protocol (JSON per message):
 - From extension:
   {"type":"request_temp_email"}
   {"type":"poll_login_email","id":"<email_id>"}
 - From server:
   {"type":"temp_email","email":"...","id":"..."}
   {"type":"login_link","link":"https://app.warp.dev/auth/..."}
   {"type":"error","message":"..."}
"""
import asyncio
import json
import logging
import re
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from src.managers.temp_email_manager import TempEmailManager

LINK_RE = re.compile(r'(https://app\.warp\.dev/auth/eyJ[a-zA-Z0-9_.-]+)')

class WsBridge:
    def __init__(self, api_key: str, host: str = '127.0.0.1', port: int = 18080):
        self.api_key = api_key
        self.host = host
        self.port = port
        self._server = None
        self._email_manager = TempEmailManager(api_key=api_key)

    async def _safe_send(self, ws: WebSocketServerProtocol, payload: dict):
        try:
            await ws.send(json.dumps(payload))
        except ConnectionClosed:
            # client went away; ignore
            return
        except Exception as e:
            logging.error(f"ws send error: {e}")

    async def _handle(self, ws: WebSocketServerProtocol):
        async for msg in ws:
            try:
                data = json.loads(msg)
            except Exception:
                continue
            t = data.get('type')
            if t == 'request_temp_email':
                try:
                    # blocking HTTP; run in thread
                    loop = asyncio.get_running_loop()
                    temp = await loop.run_in_executor(None, self._email_manager.generate_temp_email)
                    if not temp:
                        await self._safe_send(ws, {"type":"error","message":"generate_temp_email failed"})
                        continue
                    await self._safe_send(ws, {"type":"temp_email","email": temp['email'], "id": temp['id']})
                except Exception as e:
                    logging.error(f"temp email error: {e}")
                    await self._safe_send(ws, {"type":"error","message":str(e)})
            elif t == 'poll_login_email':
                email_id = data.get('id')
                if not email_id:
                    await self._safe_send(ws, {"type":"error","message":"missing id"})
                    continue
                try:
                    loop = asyncio.get_running_loop()
                    # poll in thread (blocking)
                    message = await loop.run_in_executor(None, lambda: self._email_manager.get_latest_message(email_id, timeout=120, interval=5))
                    if not message:
                        await self._safe_send(ws, {"type":"error","message":"email timeout"})
                        continue
                    html = message.get('html') or message.get('text') or ''
                    m = LINK_RE.search(html)
                    if m:
                        await self._safe_send(ws, {"type":"login_link","link": m.group(1)})
                    else:
                        await self._safe_send(ws, {"type":"error","message":"login link not found"})
                except Exception as e:
                    logging.error(f"poll email error: {e}")
                    await self._safe_send(ws, {"type":"error","message":str(e)})
            else:
                # ignore
                pass

    async def _serve(self):
        self._server = await websockets.serve(self._handle, self.host, self.port, ping_interval=20, ping_timeout=20)
        await self._server.wait_closed()

    def start_background(self):
        # Launch in background event loop
        loop = asyncio.new_event_loop()
        import threading
        def run():
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._serve())
        th = threading.Thread(target=run, name='WsBridge', daemon=True)
        th.start()
        return th, loop

    def stop(self):
        try:
            if self._server:
                self._server.close()
        except Exception:
            pass
