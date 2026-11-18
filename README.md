# gesture-mouse

맥북 웹캠으로 손을 추적해 마우스를 대신하는 로컬 프로토타입. 외부 API 없음.

## 설치 (1회)
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p models && curl -L -o models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
```
권한: 시스템 설정 > 개인정보 보호 및 보안 > **카메라**, **손쉬운 사용**에 실행하는 터미널 앱을 허용.
권한을 바꾼 뒤에는 터미널 앱을 완전히 종료(⌘Q)했다가 다시 여세요.

## 실행
```
.venv/bin/python -m gesture_mouse.app            # 실제 커서 제어 (켜기 전까지는 프리뷰)
.venv/bin/python -m gesture_mouse.app --dry-run  # 커서는 절대 안 움직이고 화면에 기록만
```

| 동작 | 방법 |
|---|---|
| 제어 켜기/끄기 | 손바닥 펴서 2초 유지, 또는 창에서 `t` |
| 커서 이동 | 검지 끝 (화면 중앙 60% 영역이 전체 화면에 대응) |
| 클릭 / 드래그 | 엄지·검지 붙였다 떼기 / 붙인 채 이동 |
| 스크롤 | 검지·중지만 펴고 위아래로 |
| 종료 | 창에서 `q`, 또는 터미널에서 Ctrl-C |

## 정지 장치
- 손이 화면에서 사라지면 즉시 제어 OFF + 눌린 버튼 해제. 다시 켜려면 직접 토글.
- Ctrl-C / `kill -INT` / `kill -TERM`: 버튼 해제 → 제어 OFF → 카메라 반환 순서로 정리.
- `kill -9`는 정리 불가. 버튼이 눌린 채 남으면 트랙패드를 한 번 클릭.
- `t`/`q` 키는 OpenCV 창에 포커스가 있을 때만 동작.

## 테스트 (Docker)
```
docker build -f Dockerfile.test -t gm-test .
docker run --rm -v "$PWD":/app gm-test
```
