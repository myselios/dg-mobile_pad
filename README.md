# gesture-mouse

맥북 웹캠으로 손을 추적해 마우스를 대신하는 로컬 프로토타입. 외부 API 없음.

## 휴대폰 트랙패드 (권장)
안드로이드 휴대폰을 맥의 무선 트랙패드로 씁니다. 휴대폰에 앱 설치 없이 브라우저로 접속합니다.

```
.venv/bin/python -m gesture_mouse.remote            # 실제 커서 제어
.venv/bin/python -m gesture_mouse.remote --dry-run  # 커서는 안 움직이고 연결만 확인
```
1. 휴대폰을 맥과 **같은 Wi-Fi**에 연결
2. 터미널에 뜬 QR을 휴대폰 카메라로 찍거나 주소를 Chrome에 입력 (주소는 실행할 때마다 바뀜)
3. 맥에서 "Python이 들어오는 연결을 허용" 창이 뜨면 허용

| 동작 | 방법 |
|---|---|
| 커서 이동 | 한 손가락 문지르기 (빠르게 문지를수록 멀리) |
| 클릭 / 더블클릭 | 탭 / 두 번 탭 |
| 드래그 | 두 번 탭한 뒤 두 번째 손가락을 떼지 않고 끌기 |
| 스크롤 | 두 손가락 위아래 |
| 우클릭 | 두 손가락 탭 |
| 유튜브 / 이전 / 음성검색 / 다음 | 화면 아래 버튼 |
| 제어 켜기/끄기 | 오른쪽 위 ON/OFF |

안전: 실행마다 새 비밀 토큰이 든 주소로만 접속, 한 번에 휴대폰 한 대. 연결이 끊기면(화면 꺼짐, Wi-Fi 끊김) 즉시 버튼 해제 + 제어 OFF. Ctrl-C로 종료.
HTTP라 같은 Wi-Fi의 누군가가 트래픽을 엿보면 토큰이 보일 수 있습니다. 집 Wi-Fi에서만 쓰세요.

---

# 카메라 제스처 모드 (실험용, 더 이상 개선하지 않음)

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
| 제어 켜기/끄기 | **주먹 1초**, 또는 창에서 `t` |
| 커서 이동 | 검지 끝 (화면 중앙 60% 영역이 전체 화면에 대응) |
| 클릭 / 드래그 | 엄지·검지 붙였다 떼기 / 붙인 채 이동 |
| 스크롤 | 검지·중지만 펴고 위아래로 |
| 유튜브 열기 (Safari) | 손바닥 펴고 1초 가만히 |
| 다음 / 이전 영상 | 손바닥 편 채 왼쪽 / 오른쪽으로 빠르게 휘두르기 |
| 음성검색 | 🤙 (엄지·새끼만 펴기) 0.5초 |
| 종료 | 창에서 `q`, 또는 터미널에서 Ctrl-C |

유튜브 기능도 제어가 켜져 있을 때만 동작합니다.

### Safari 1회 설정 (다음/이전/음성검색)
1. Safari > 설정 > 고급 > **웹 개발자용 기능 보기** 켜기
2. 메뉴 막대 개발자용 > **Apple Events의 JavaScript 허용** 체크
3. 처음 실행 시 "터미널이 Safari를 제어하려고 합니다" 창이 뜨면 허용

이전 영상: 재생목록 안에서는 이전 영상, 아니면 이전 페이지로 돌아갑니다.
음성검색: 마이크 버튼이 없으면 검색창에 커서만 놓습니다.

## 정지 장치
- **가장 빠른 비상정지: 손을 카메라 밖으로 빼기.** 창 포커스와 상관없이 버튼 즉시 해제, 1초 뒤 제어 OFF.
- 카메라 프레임이 1초 이상 멈추면 자동으로 제어 OFF.
- 손이 사라지면 눌린 버튼은 즉시 해제, 1초 넘게 안 보이면 제어 OFF. 다시 켜려면 직접 토글.
- Ctrl-C / `kill -INT` / `kill -TERM`: 버튼 해제 → 제어 OFF → 카메라 반환 순서로 정리.
- `kill -9`는 정리 불가. 버튼이 눌린 채 남으면 트랙패드를 한 번 클릭.
- `t`/`q` 키는 OpenCV 창에 포커스가 있을 때만 동작.

## 테스트 (Docker)
```
docker build -f Dockerfile.test -t gm-test .
docker run --rm -v "$PWD":/app gm-test
```
