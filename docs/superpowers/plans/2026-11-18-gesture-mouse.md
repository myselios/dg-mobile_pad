# 맥 제스처 마우스 구현 계획서

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**목표:** 맥북 내장 웹캠으로 손을 추적해 커서 이동·클릭·스크롤을 하는 로컬 프로그램(프로토타입)을 만든다.

**구조:** 판정 로직(제스처·필터·좌표 매핑·안전 상태)은 표준 라이브러리만 쓰는 순수 모듈로 두고 Docker에서 단위 테스트한다. 카메라·MediaPipe·CGEvent를 쓰는 실행부는 macOS 전용이라 맥의 프로젝트 가상환경(`.venv`)에서 실행한다. 모든 마우스 동작은 `Controller`를 거치며, `Controller`가 꺼져 있으면 아무 이벤트도 나가지 않는다.

**기술 스택:** Python 3.15(Homebrew), mediapipe 1.2.3(Hand Landmarker, VIDEO 모드), OpenCV(mediapipe가 설치하는 `opencv-contrib-python`), pyobjc-framework-Quartz 13.0, pytest, Docker(`python:3.15-slim`)

**스펙:** 사용자 브리프 「맥 제스처 마우스 개발 브리프」(2026-11-18 대화)

## 확인된 환경 (2026-11-18)

| 항목 | 값 |
|---|---|
| macOS | 26.6 (25G72), arm64 |
| Python | /opt/homebrew/bin/python3 → 3.15.2 (uv/pyenv 없음) |
| 카메라 | "MacBook Pro 카메라" 인식됨 |
| Docker | 29.9.3, linux/aarch64, `python:3.15-slim` 태그 존재 |
| mediapipe 1.2.3 | `py3-none-macosx_11_0_arm64` wheel 있음. Python 3.15에서 실제 동작은 설치 후 확인 필요 |
| pyobjc-framework-Quartz 13.0 | cp315 arm64 wheel 있음 |

## 설치 계획 (실행 전 사용자 확인 필요)

- `python3 -m venv .venv` → 시스템 Python은 건드리지 않음
- `.venv/bin/pip install mediapipe pyobjc-framework-Quartz pytest`
  - numpy와 `opencv-contrib-python`은 mediapipe가 같이 설치함. `opencv-python`을 따로 설치하면 충돌하므로 설치하지 않음
- 모델 파일 1회 다운로드: `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task` → `models/hand_landmarker.task` (git에서 제외)
- Docker 테스트 이미지: `python:3.15-slim` + pytest만 설치
- 권한(사용자가 직접 허용): 시스템 설정 → 개인정보 보호 및 보안 → **카메라**, **손쉬운 사용**. 권한은 python이 아니라 **실행한 터미널 앱**(Terminal/iTerm 등)에 부여됨
- **대체 방안:** mediapipe가 3.15에서 import나 추론에 실패하면, `brew install python@3.12`로 3.12 가상환경을 만들어 다시 시도한다 (사용자 확인 후)

## 전역 제약

- 외부 API·LLM 호출 없음. 네트워크는 패키지 설치와 모델 1회 다운로드에만 사용
- 실행하면 기본은 프리뷰 모드: 오버레이만 보이고 마우스 이벤트는 0건
- 제어 ON은 오직 두 경로: OpenCV 창에서 `t` 키, 또는 손바닥을 펴서 2.0초 유지. 자동으로 켜지는 경로는 없음
- 손을 놓치거나 프레임 읽기가 실패하면 즉시 제어 OFF + 눌린 버튼 해제. 손이 다시 잡혀도 자동으로 다시 켜지지 않음
- 종료 정리 순서는 고정: 버튼 해제 → 제어 OFF → 카메라 반환
- Task 3(안전 장치)이 끝나기 전에는 `QuartzMouse`를 만들거나 연결하지 않음
- `gesture_mouse/gestures.py`, `gesture_mouse/safety.py`는 표준 라이브러리만 import (Docker 테스트 가능해야 함)

## 리뷰 포인트 (테스트가 직접 다루지 않는 실패 모드)

1. **모니터 여러 대:** 주 모니터에만 매핑함. 보조 모니터로는 커서가 가지 않는 것이 예상 동작 → `map_to_screen` 범위 클램프 테스트로 고정(Task 4)
2. **핀치 순간 커서 튐:** 엄지를 붙일 때 검지 끝이 움직여 클릭 위치가 어긋남 → 눌린 동안 커서 이동량을 줄이는 것은 튜닝 항목. 우선은 One Euro 필터로 완화하고 실사용 결과를 보고 결정
3. **손바닥 토글 반복:** 손바닥을 계속 펴고 있으면 ON/OFF가 2초마다 반복될 수 있음 → `HoldTimer`는 손바닥을 한 번 내려야 다시 발동(Task 2 테스트)
4. **스크롤 중 클릭:** 두 손가락 자세에서 엄지가 검지에 닿으면 클릭이 날 수 있음 → 스크롤 자세에서는 핀치 판정을 무시(Task 6 테스트)
5. **창 포커스 없을 때의 정지:** `t`/ESC 키는 OpenCV 창에 포커스가 있을 때만 동작 → 전역 정지 수단은 Ctrl-C/`kill -INT`와 "카메라에서 손 빼기"(손 소실 → OFF) 두 가지로 문서화

---

## 파일 구조

| 파일 | 역할 |
|---|---|
| `gesture_mouse/gestures.py` | 순수 함수: 손가락 펴짐, 손바닥/스크롤 자세, 핀치 비율, `PinchDetector`, `HoldTimer`, `OneEuroFilter`, `map_to_screen` |
| `gesture_mouse/safety.py` | `Mouse` 프로토콜, `LogMouse`(기록용/프리뷰), `Controller`(ON/OFF·버튼 상태), `cleanup()` |
| `gesture_mouse/mouse.py` | `QuartzMouse`(CGEvent), `screen_size()`, `can_post_events()` — macOS 전용 |
| `gesture_mouse/app.py` | 카메라 루프, MediaPipe, 오버레이, 키 입력, 시그널 처리. `python -m gesture_mouse.app`로 실행 |
| `tests/fixtures.py` | 21점 랜드마크 fixture: `open_palm()`, `point_index()`, `scroll_pose()`, `fist()`, `pinch(ratio)` |
| `tests/test_gestures.py`, `tests/test_safety.py` | 단위 테스트 |
| `Dockerfile.test`, `requirements.txt`, `.gitignore`, `README.md` | 환경 |

랜드마크 타입: `Landmarks = list[tuple[float, float]]` (길이 21, MediaPipe 정규화 x,y). MediaPipe 인덱스: 0 손목, 4 엄지끝, 3 엄지IP, 5/9/13/17 MCP, 6/10/14/18 PIP, 8/12/16/20 손가락끝.

---

### Task 1: 환경 준비 + 카메라 프리뷰와 랜드마크 오버레이 (마일스톤 1)

**Files:**
- Create: `requirements.txt`, `.gitignore`(`.venv/`, `models/`, `__pycache__/`), `gesture_mouse/__init__.py`, `gesture_mouse/app.py`, `README.md`

**Interfaces:**
- Produces: `python -m gesture_mouse.app [--camera N]`. 내부에 `to_landmarks(result) -> Landmarks | None` (첫 번째 손만 사용, `num_hands=1`)

- [ ] **Step 1:** `git init`, venv 생성, `requirements.txt`(`mediapipe==1.2.3`, `pyobjc-framework-Quartz==13.0`, `pytest`) 설치, 모델 다운로드
- [ ] **Step 2:** mediapipe 동작 확인 — Run: `.venv/bin/python -c "import mediapipe as mp; print(mp.__version__, mp.tasks.vision.HandLandmarker)"` / Expected: `1.2.3`와 클래스 출력. 실패하면 위 대체 방안으로 전환하고 사용자에게 보고
- [ ] **Step 3:** `app.py` 작성: `cv2.VideoCapture(0)` → 좌우 반전 → `HandLandmarker`(VIDEO 모드, `detect_for_video(mp_image, timestamp_ms)`, 타임스탬프는 `time.monotonic()` 기반 증가 ms) → 21점과 뼈대를 그림. 화면 좌상단에 `MODE: PREVIEW`, FPS 표시. 시작 시 카메라·손쉬운 사용 권한 안내를 콘솔에 출력. 카메라 첫 `read()`가 실패하면 권한 안내를 출력하고 종료(코드 1)
- [ ] **Step 4:** 수동 확인 — Run: `.venv/bin/python -m gesture_mouse.app` / Expected: 미러 화면에 손 21점이 따라다님. 손을 빼면 점이 사라짐. `q` 키로 종료
- [ ] **Step 5:** 커밋 `feat: camera preview with hand landmark overlay`

### Task 2: 제스처 판정 순수 함수 + Docker 테스트

**Files:**
- Create: `gesture_mouse/gestures.py`, `tests/fixtures.py`, `tests/test_gestures.py`, `Dockerfile.test`

**Interfaces:**
- Produces:
  - `finger_extended(lm: Landmarks, finger: str) -> bool` — finger ∈ `thumb,index,middle,ring,pinky`. 손가락: 끝–손목 거리 > PIP–손목 거리. 엄지: dist(4,9) > dist(3,9)
  - `is_open_palm(lm) -> bool` — 다섯 손가락 모두 펴짐
  - `is_scroll_pose(lm) -> bool` — 검지·중지 펴짐, 약지·새끼 접힘
  - `pinch_ratio(lm) -> float` — dist(4,8) / dist(0,9) (손 크기로 정규화)
  - `class HoldTimer(hold_s=2.0)`: `update(active: bool, now: float) -> bool`, 연속 유지가 hold_s에 처음 도달한 프레임에만 True. active가 False가 되기 전까지 다시 발동하지 않음

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_open_palm():        assert is_open_palm(open_palm()) and not is_open_palm(fist())
def test_scroll_pose():      assert is_scroll_pose(scroll_pose()) and not is_scroll_pose(open_palm())
def test_index_only():       lm = point_index(); assert finger_extended(lm, "index") and not finger_extended(lm, "middle")
def test_pinch_ratio_scale_invariant():
    assert abs(pinch_ratio(pinch(0.2)) - pinch_ratio(scale(pinch(0.2), 0.5))) < 1e-6
def test_hold_fires_once():
    h = HoldTimer(2.0)
    assert [h.update(True, t) for t in (0, 1.9, 2.0, 3, 10)] == [False, False, True, False, False]
    h.update(False, 11); assert h.update(True, 12) is False and h.update(True, 14) is True
```

- [ ] **Step 2:** `Dockerfile.test` 작성(`FROM python:3.15-slim`, `RUN pip install pytest`, `WORKDIR /app`, `CMD ["pytest","-q"]`), 실패 확인 — Run: `docker build -f Dockerfile.test -t gm-test . && docker run --rm -v "$PWD":/app gm-test` / Expected: ImportError로 FAIL
- [ ] **Step 3:** `gestures.py`에 위 함수들 구현 (stdlib `math`만 사용)
- [ ] **Step 4:** 같은 명령으로 PASS 확인
- [ ] **Step 5:** 커밋 `feat: pure gesture classifiers with docker tests`

### Task 3: 안전 장치 — 토글, 손 소실 OFF, 비상정지 (마일스톤 2)

**Files:**
- Create: `gesture_mouse/safety.py`, `tests/test_safety.py`
- Modify: `gesture_mouse/app.py`

**Interfaces:**
- Consumes: `is_open_palm`, `HoldTimer`
- Produces:
  - `class Mouse(Protocol)`: `move(x: int, y: int)`, `button(down: bool)`, `scroll(dy: int)`
  - `class LogMouse`: `calls: list[tuple]`. 예: `("move", x, y)`, `("button", True)`, `("scroll", dy)`
  - `class Controller(mouse: Mouse)`: `enabled: bool`(초기 False), `button_down: bool`, `toggle()`, `move(x, y)`, `press()`, `release()`, `scroll(dy)`, `hand_lost()`, `shutdown()`. `enabled`가 False면 `move/press/scroll`은 아무것도 보내지 않음. `release()`는 버튼이 눌려 있을 때만 `button(False)`를 보냄. `toggle()`로 끌 때와 `hand_lost()`·`shutdown()`은 먼저 `release()`한 뒤 `enabled=False`로 바꿈
  - `cleanup(controller: Controller, release_camera: Callable[[], None]) -> None` — 순서: `controller.shutdown()` → `release_camera()`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_starts_disabled_and_sends_nothing():
    m = LogMouse(); c = Controller(m); c.move(1, 1); c.press(); c.scroll(3); assert m.calls == []
def test_hand_lost_releases_then_disables():
    m = LogMouse(); c = Controller(m); c.toggle(); c.press(); c.hand_lost()
    assert m.calls[-1] == ("button", False) and not c.enabled and not c.button_down
def test_no_auto_reenable_after_hand_lost():
    m = LogMouse(); c = Controller(m); c.toggle(); c.hand_lost(); c.move(5, 5); assert ("move", 5, 5) not in m.calls
def test_toggle_off_releases_button():
    m = LogMouse(); c = Controller(m); c.toggle(); c.press(); c.toggle(); assert m.calls[-1] == ("button", False)
def test_cleanup_order():
    log = []; m = LogMouse(); c = Controller(m); c.toggle(); c.press()
    cleanup(c, lambda: log.append(("camera", len(m.calls), c.enabled)))
    assert m.calls[-1] == ("button", False) and log == [("camera", len(m.calls), False)]
def test_release_without_press_sends_nothing():
    m = LogMouse(); c = Controller(m); c.toggle(); c.release(); assert m.calls == []
```

- [ ] **Step 2:** Docker로 FAIL 확인
- [ ] **Step 3:** `safety.py` 구현
- [ ] **Step 4:** Docker로 PASS 확인
- [ ] **Step 5:** `app.py` 연결 — 이 단계의 mouse는 `LogMouse`(실제 이벤트 없음). 규칙:
  - `t` 키 또는 `HoldTimer.update(is_open_palm(lm), now)`가 True → `controller.toggle()`
  - 손이 없음, 또는 `cap.read()` 실패 → `controller.hand_lost()` (오버레이에 `CONTROL OFF (hand lost)` 표시)
  - 메인 루프를 `try/finally: cleanup(controller, cap.release)`로 감싸고, `signal.signal(SIGTERM, ...)`에서 `SystemExit`를 발생시켜 SIGTERM도 같은 경로로 정리. Ctrl-C는 기본 `KeyboardInterrupt`로 같은 finally를 탐
  - 정리 각 단계에서 `[cleanup] button released / control off / camera released`를 출력
  - 오버레이: `MODE: PREVIEW` 또는 `CONTROL ON`, LogMouse의 최근 호출 3개
- [ ] **Step 6: 수동 검증(기기 의존)** — 결과는 확인한 것과 못 한 것을 나눠 보고
  - 손바닥 2초 → ON, 다시 2초 → OFF. 계속 펴고 있어도 반복 토글되지 않음
  - ON 상태에서 손을 빼면 즉시 OFF. 손을 다시 넣어도 OFF 유지
  - ON 상태에서 터미널에 Ctrl-C → 콘솔에 정리 3줄이 순서대로 출력, 카메라 표시등 꺼짐
  - 다른 터미널에서 `kill -INT <pid>`와 `kill -TERM <pid>` → 같은 출력
  - **검증 불가로 명시할 경로:** `kill -9`(정리 불가. 버튼이 눌린 채 남으면 트랙패드를 한 번 클릭해 해제), OpenCV 창 포커스가 없을 때의 키 입력
- [ ] **Step 7:** 커밋 `feat: safety controller with toggle, hand-loss off, signal cleanup`

### Task 4: 검지 끝 → 커서 이동 (마일스톤 3)

**Files:**
- Create: `gesture_mouse/mouse.py`
- Modify: `gesture_mouse/gestures.py`, `tests/test_gestures.py`, `gesture_mouse/app.py`

**Interfaces:**
- Produces:
  - `class OneEuroFilter(min_cutoff=1.0, beta=0.01, d_cutoff=1.0)`: `__call__(x: float, t: float) -> float`, `reset()`. 표준 One Euro 알고리즘(Casiez 2012)
  - `map_to_screen(x: float, y: float, width: int, height: int, margin: float = 0.2) -> tuple[int, int]` — 입력은 이미 미러링된 정규화 좌표. `[margin, 1-margin]`를 `[0, width-1]`로 선형 매핑하고 범위 밖은 클램프
  - `mouse.py`: `screen_size() -> tuple[int, int]` (`CGDisplayBounds(CGMainDisplayID())`, 포인트 단위), `can_post_events() -> bool` (`CGPreflightPostEventAccess`. pyobjc에 없으면 None을 반환하고 안내만 출력), `class QuartzMouse(Mouse)`: `CGEventCreateMouseEvent` + `CGEventPost(kCGHIDEventTap, …)`. 버튼이 눌린 동안 move는 `kCGEventLeftMouseDragged`로 보냄

- [ ] **Step 1: 실패하는 테스트**

```python
def test_map_center():  assert map_to_screen(0.5, 0.5, 1000, 800) == (500, 400)  # 반올림 규칙: round
def test_map_clamps():  assert map_to_screen(0.0, 1.0, 1000, 800) == (0, 799) and map_to_screen(0.2, 0.8, 1000, 800) == (0, 799)
def test_one_euro_constant():  f = OneEuroFilter(); assert all(abs(f(0.3, i / 30) - 0.3) < 1e-9 for i in range(30))
def test_one_euro_reduces_jitter():  # 0.5±0.01 교대 입력 60프레임 → 출력 분산 < 입력 분산 / 4
    ...
```

- [ ] **Step 2:** Docker로 FAIL → **Step 3:** 구현 → **Step 4:** PASS
- [ ] **Step 5:** `app.py`: `--dry-run` 플래그(기본 False)가 있으면 `LogMouse`, 없으면 `QuartzMouse`를 씀. 그래도 `Controller`가 OFF로 시작하므로 프리뷰가 기본. 검지끝(8) x,y → 각각 `OneEuroFilter` → `map_to_screen` → `controller.move`. 손 소실 시 필터 `reset()`. 시작할 때 `can_post_events()`가 False면 손쉬운 사용 권한 안내를 출력
- [ ] **Step 6: 수동 검증** — ON 후 검지로 화면 네 모서리에 도달하는지, 손을 멈췄을 때 커서 떨림이 눈에 띄지 않는지, OFF에서 커서가 안 움직이는지 확인. 떨림이 심하면 `min_cutoff`/`beta` 조정값을 기록
- [ ] **Step 7:** 커밋 `feat: index fingertip cursor with one euro smoothing`

### Task 5: 핀치 → 클릭 (마일스톤 4)

**Files:** Modify `gesture_mouse/gestures.py`, `tests/test_gestures.py`, `gesture_mouse/app.py`

**Interfaces:**
- Produces: `class PinchDetector(press: float = 0.25, release: float = 0.40, cooldown_s: float = 0.3)`: `update(ratio: float, now: float) -> str | None`(`"down"`/`"up"`/None), `pressed: bool`, `reset()`. ratio < press이면 down. 눌린 상태에서 ratio > release이면 up. 마지막 up 이후 cooldown_s 이내의 down은 무시

- [ ] **Step 1: 실패하는 테스트**

```python
def test_hysteresis():
    p = PinchDetector(); seq = [(0.5,0), (0.2,0.1), (0.3,0.2), (0.35,0.3), (0.45,0.4)]
    assert [p.update(r, t) for r, t in seq] == [None, "down", None, None, "up"]
def test_cooldown():
    p = PinchDetector(); p.update(0.2, 0); p.update(0.5, 0.1)
    assert p.update(0.2, 0.2) is None and p.update(0.5, 0.25) is None and p.update(0.2, 0.5) == "down"
def test_reset_clears_pressed():  p = PinchDetector(); p.update(0.2, 0); p.reset(); assert not p.pressed
```

- [ ] **Step 2:** FAIL → **Step 3:** 구현 → **Step 4:** PASS
- [ ] **Step 5:** `app.py`: `"down"` → `controller.press()`, `"up"` → `controller.release()`. 손 소실·토글 OFF 시 `PinchDetector.reset()`. 오버레이에 pinch_ratio 수치 표시(튜닝용)
- [ ] **Step 6: 수동 검증** — 메모장 같은 창에서 클릭 10회 시도 → 오클릭/누락 횟수 기록. 핀치한 채 손 빼기 → 버튼이 풀림(텍스트 드래그 선택이 끝나는지로 확인)
- [ ] **Step 7:** 커밋 `feat: pinch click with hysteresis and cooldown`

### Task 6: 두 손가락 스크롤 (마일스톤 5)

**Files:** Modify `gesture_mouse/gestures.py`, `tests/test_gestures.py`, `gesture_mouse/mouse.py`, `gesture_mouse/app.py`

**Interfaces:**
- Produces: `scroll_delta(prev_y: float, y: float, gain: float = 2000.0, deadzone: float = 0.005) -> int` — 정규화 y 변화량 × gain, |Δy| < deadzone이면 0. 손을 위로 올리면 양수(위로 스크롤). `QuartzMouse.scroll(dy)`: `CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitPixel, 1, dy)`

- [ ] **Step 1: 실패하는 테스트**

```python
def test_scroll_direction():  assert scroll_delta(0.5, 0.45) > 0 and scroll_delta(0.5, 0.55) < 0
def test_scroll_deadzone():   assert scroll_delta(0.5, 0.503) == 0
```

- [ ] **Step 2:** FAIL → **Step 3:** 구현 → **Step 4:** PASS
- [ ] **Step 5:** `app.py`: `is_scroll_pose(lm)`일 때 커서 이동과 핀치 판정을 멈추고, 검지·중지 끝 y 평균으로 `scroll_delta` → `controller.scroll`. 자세가 바뀌거나 손을 놓치면 prev_y 초기화. 스크롤 진입 시 버튼이 눌려 있으면 `release()`
- [ ] **Step 6: 수동 검증** — 브라우저 긴 페이지에서 위/아래 스크롤, 멈춘 손에서 스크롤 미발생, 스크롤 중 오클릭 없음 확인
- [ ] **Step 7:** 커밋 `feat: two-finger scroll`

---

## 하지 않는 것 (이번 범위 밖)

- 설정 파일·GUI 설정 화면 (튜닝값은 코드 상수)
- 우클릭·더블클릭 전용 제스처, 여러 모니터, 두 손 인식
- SwiftUI 네이티브 앱 전환, 자동 시작(로그인 항목)

---

## 추가 (2026-11-18): 유튜브 제스처

사용자 요청으로 한 모드에 섞음. 제스처 재배치: 주먹 2초 = 제어 켜기/끄기(손바닥에서 이동), 정지한 손바닥 1초 = Safari에서 유튜브 열기, 손바닥 좌/우 스와이프 = 다음/이전 영상, 🤙 0.5초 = 음성검색(마이크 버튼, 없으면 검색창 포커스). 모든 동작은 제어 ON일 때만. 구현: `gestures.py`(is_fist, is_call_pose, SwipeDetector, OK사인 오인 방지), `frame.py`(통합), `actions.py`(Safari JS via AppleScript), `safety.LogActions`(dry-run).

---

## 방향 전환 (2026-11-18): 안드로이드 휴대폰 웹 트랙패드

카메라 인식 품질 문제로 사용자가 "휴대폰만"을 선택. 카메라 모드 코드는 남기되 더 손대지 않음.

- 맥: `python -m gesture_mouse.remote [--dry-run] [--port 8765]` — websockets 서버가 같은 포트에서 HTTP(트랙패드 페이지)와 WebSocket을 모두 처리. 실행마다 `secrets.token_urlsafe` 토큰 생성, 토큰이 맞는 단일 클라이언트만 허용. 주소는 터미널 QR로 표시.
- 휴대폰 페이지(`gesture_mouse/remote_page.html`): 한 손가락 이동, 탭=클릭, 두 손가락 탭=우클릭, 두 손가락 위아래=스크롤, 두 번 탭 후 끌기=드래그, 버튼(유튜브/이전/음성/다음/ON·OFF).
- `gesture_mouse/remote_logic.py`(stdlib, Docker 테스트): `RemoteHandler.handle(msg)` → `Controller`. 상대 이동 + 가속, 화면 클램프.
- 안전: 연결 시 ON, 연결 끊김/핑 실패 → `shutdown()`(버튼 해제+OFF), 휴대폰 OFF 버튼, Ctrl-C 정리 경로 유지.
