# gesture-mouse

맥북 웹캠으로 손을 추적해 마우스를 대신하는 로컬 프로토타입.

## 설치 (1회)
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p models && curl -L -o models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
```
권한: 시스템 설정 > 개인정보 보호 및 보안 > **카메라**, **손쉬운 사용**에 실행하는 터미널 앱을 허용.

## 실행
```
.venv/bin/python -m gesture_mouse.app
```
`q`: 종료
