import asyncio
import json
import urllib.error
import urllib.request

import pytest
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import InvalidStatus

from gesture_mouse.remote import make_app
from gesture_mouse.remote_logic import RemoteHandler
from gesture_mouse.safety import Controller, LogActions, LogMouse

TOKEN = "secret-token"


def run(scenario):
    async def main():
        m = LogMouse(); c = Controller(m)
        h = RemoteHandler(c, LogActions(), (1000, 800), lambda: (500, 400))
        pr, wh = make_app(h, TOKEN)
        async with serve(wh, "127.0.0.1", 0, process_request=pr) as server:
            port = server.sockets[0].getsockname()[1]
            await scenario(port, m, c)
    asyncio.run(main())


def http_get(url):
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, ""


def test_page_needs_token():
    async def s(port, m, c):
        status, _ = await asyncio.to_thread(http_get, f"http://127.0.0.1:{port}/?k=wrong")
        assert status == 403
        status, body = await asyncio.to_thread(http_get, f"http://127.0.0.1:{port}/?k={TOKEN}")
        assert status == 200 and "WebSocket" in body
    run(s)


def test_ws_needs_token():
    async def s(port, m, c):
        with pytest.raises(InvalidStatus):
            async with connect(f"ws://127.0.0.1:{port}/ws?k=wrong"):
                pass
    run(s)


def test_ws_flow_and_disconnect_releases():
    async def s(port, m, c):
        async with connect(f"ws://127.0.0.1:{port}/ws?k={TOKEN}") as ws:
            await ws.send(json.dumps({"t": "on"}))
            assert json.loads(await ws.recv()) == {"on": True}
            await ws.send(json.dumps({"t": "down"}))
            await ws.send("garbage{")
            await ws.send(json.dumps({"t": "move", "dx": 5, "dy": 0}))
            await ws.send(json.dumps({"t": "off"}))
            await ws.recv()
            await ws.send(json.dumps({"t": "on"})); await ws.recv()
            await ws.send(json.dumps({"t": "down"}))
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.2)
        assert m.calls[-1] == ("button", False) and not c.enabled and not c.button_down
    run(s)


def test_second_phone_rejected():
    async def s(port, m, c):
        async with connect(f"ws://127.0.0.1:{port}/ws?k={TOKEN}") as first:
            await first.send(json.dumps({"t": "on"})); await first.recv()
            async with connect(f"ws://127.0.0.1:{port}/ws?k={TOKEN}") as second:
                await second.wait_closed()
                assert second.close_code == 1013
            assert c.enabled  # first phone unaffected
    run(s)
