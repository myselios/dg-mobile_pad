"""Phone-as-trackpad server. Run: .venv/bin/python -m gesture_mouse.remote

Serves the trackpad page and a WebSocket on one port. A fresh secret token per run is required
for both; only one phone at a time. Phone disconnect or Ctrl-C -> button up, control off.
"""
import argparse
import asyncio
import json
import secrets
import signal
import socket
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from websockets.asyncio.server import serve
from websockets.datastructures import Headers
from websockets.http11 import Response

from gesture_mouse.remote_logic import RemoteHandler
from gesture_mouse.safety import Controller, LogActions, LogMouse

PAGE = Path(__file__).with_name("remote_page.html")


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # UDP connect sends nothing; it just picks the outgoing interface
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def make_app(handler, token):
    """Returns (process_request, ws_handler) for websockets.serve."""
    state = {"client": None}

    def process_request(connection, request):
        url = urlparse(request.path)
        if not secrets.compare_digest(parse_qs(url.query).get("k", [""])[0], token):
            return connection.respond(HTTPStatus.FORBIDDEN, "forbidden\n")
        if url.path == "/":
            body = PAGE.read_bytes()
            return Response(200, "OK", Headers([("Content-Type", "text/html; charset=utf-8"),
                                                ("Content-Length", str(len(body))),
                                                ("Cache-Control", "no-store")]), body)
        if url.path == "/ws":
            return None  # go on with the WebSocket handshake
        return connection.respond(HTTPStatus.NOT_FOUND, "not found\n")

    async def ws_handler(connection):
        if state["client"] is not None:
            await connection.close(1013, "another phone is connected")
            return
        state["client"] = connection
        print("[remote] phone connected", flush=True)
        try:
            async for raw in connection:
                try:
                    msg = json.loads(raw)
                except ValueError:
                    msg = None
                handler.handle(msg)
                if isinstance(msg, dict) and msg.get("t") in ("on", "off"):
                    await connection.send(json.dumps({"on": handler.c.enabled}))
        finally:
            handler.disconnected()
            state["client"] = None
            print("[remote] phone disconnected: button released, control off", flush=True)

    return process_request, ws_handler


def print_qr(url):
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.print_ascii(invert=True)
    except Exception as e:  # the URL below still works
        print(f"[주의] QR 표시 실패: {e}")


async def amain(args):
    if args.dry_run:
        mouse, actions, screen = LogMouse(), LogActions(), (1920, 1080)
        get_pos = lambda: (960, 540)  # noqa: E731
    else:
        from gesture_mouse.actions import SafariYouTube
        from gesture_mouse.mouse import QuartzMouse, can_post_events, screen_size
        mouse, actions, screen = QuartzMouse(), SafariYouTube(), screen_size()
        get_pos = mouse.position
        if can_post_events() is False:
            print("[주의] 손쉬운 사용 권한이 없어 커서 이벤트가 무시됩니다. "
                  "시스템 설정 > 개인정보 보호 및 보안 > 손쉬운 사용에서 터미널 앱을 허용하세요.", flush=True)
    controller = Controller(mouse)
    handler = RemoteHandler(controller, actions, screen, get_pos)
    token = secrets.token_urlsafe(16)
    process_request, ws_handler = make_app(handler, token)

    stop = asyncio.get_running_loop().create_future()
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(sig, lambda: stop.done() or stop.set_result(None))
    try:
        async with serve(ws_handler, args.host, args.port, process_request=process_request,
                         ping_interval=2, ping_timeout=3, max_size=4096):
            url = f"http://{lan_ip()}:{args.port}/?k={token}"
            print("\n휴대폰을 맥과 같은 Wi-Fi에 연결하고, 카메라로 QR을 찍거나 아래 주소를 여세요:\n")
            print_qr(url)
            print(f"\n  {url}\n\n종료: Ctrl-C" + ("   (dry-run: 커서는 움직이지 않음)" if args.dry_run else ""), flush=True)
            await stop
    finally:
        controller.shutdown()
        print("\n[cleanup] button released, control off", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="0.0.0.0", help="interface to listen on (0.0.0.0 = reachable on the LAN)")
    ap.add_argument("--dry-run", action="store_true", help="never post real mouse events")
    asyncio.run(amain(ap.parse_args(argv)))


if __name__ == "__main__":
    main()
