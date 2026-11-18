"""YouTube actions in Safari (macOS only).

Page buttons are clicked via JavaScript (works regardless of the Korean/English input source).
Needs, once: Safari > 설정 > 고급 > '웹 개발자용 기능 보기' on, then 개발자용 메뉴 > 'Apple Events의 JavaScript 허용'.
macOS will also ask once to allow the terminal app to control Safari.
"""
import json
import subprocess
import threading

JS = {
    "next_video": "var b=document.querySelector('.ytp-next-button');"
                  "if(b){b.click();'next'}else{'no next button'}",
    # The previous button only shows inside playlists; otherwise go back a page.
    "prev_video": "var b=document.querySelector('.ytp-prev-button');"
                  "if(b&&b.offsetParent!==null){b.click();'prev'}else{history.back();'history back'}",
    "voice_search": "var b=document.querySelector('#voice-search-button button');"
                    "if(b){b.click();'voice'}else{var i=document.querySelector('input[name=search_query]');"
                    "if(i){i.focus();'no mic button: search box focused'}else{'not a YouTube page'}}",
}
SETUP_HELP = ("[안내] Safari > 설정 > 고급 > '웹 개발자용 기능 보기'를 켜고, "
              "개발자용 메뉴 > 'Apple Events의 JavaScript 허용'을 체크하세요.")


def applescript(js):
    # json.dumps gives a double-quoted string with \" and \\ escapes, which AppleScript accepts.
    return ('tell application "Safari"\nactivate\n'
            f"do JavaScript {json.dumps(js)} in current tab of front window\nend tell")


def _run(name, script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
    out = (r.stdout or r.stderr).strip()
    print(f"[action] {name}: {out}", flush=True)
    if r.returncode and "JavaScript" in out:
        print(SETUP_HELP, flush=True)


class SafariYouTube:
    def open_youtube(self):
        subprocess.Popen(["open", "-a", "Safari", "https://www.youtube.com"])
        print("[action] open_youtube", flush=True)

    def _js(self, name):
        # Off the camera loop so a slow or blocked AppleScript never stalls tracking.
        threading.Thread(target=_run, args=(name, applescript(JS[name])), daemon=True).start()

    def next_video(self): self._js("next_video")
    def prev_video(self): self._js("prev_video")
    def voice_search(self): self._js("voice_search")
