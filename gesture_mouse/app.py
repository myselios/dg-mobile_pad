"""Webcam hand tracking preview. Run: .venv/bin/python -m gesture_mouse.app"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp

MODEL = Path(__file__).resolve().parent.parent / "models" / "hand_landmarker.task"
CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
               (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]
PERMISSION_HELP = """\
[권한 안내] 시스템 설정 > 개인정보 보호 및 보안 에서 '이 프로그램을 실행한 터미널 앱'에 허용:
  - 카메라: 손 인식에 필요
  - 손쉬운 사용: 커서 이동/클릭에 필요 (프리뷰만 볼 때는 불필요)
  권한을 바꾼 뒤에는 터미널 앱을 완전히 종료했다가 다시 실행하세요."""


def to_landmarks(result):
    """First hand's 21 (x, y) normalized points, or None."""
    if not result.hand_landmarks:
        return None
    return [(p.x, p.y) for p in result.hand_landmarks[0]]


def draw(frame, lm, lines):
    h, w = frame.shape[:2]
    if lm:
        pts = [(int(x * w), int(y * h)) for x, y in lm]
        for a, b in CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], (255, 255, 255), 2)
        for p in pts:
            cv2.circle(frame, p, 4, (0, 200, 255), -1)
    for i, text in enumerate(lines):
        cv2.putText(frame, text, (10, 30 + 28 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args(argv)
    print(PERMISSION_HELP)

    cap = cv2.VideoCapture(args.camera)
    ok, frame = cap.read()
    if not ok:
        print("[오류] 카메라 프레임을 읽지 못했습니다. 카메라 권한을 확인하세요.", file=sys.stderr)
        cap.release()
        return 1

    vision = mp.tasks.vision
    options = vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL)),
        running_mode=vision.RunningMode.VIDEO, num_hands=1)
    t0, last_ts, fps, prev = time.monotonic(), -1, 0.0, time.monotonic()
    with vision.HandLandmarker.create_from_options(options) as landmarker:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            ts = max(int((time.monotonic() - t0) * 1000), last_ts + 1)  # VIDEO mode needs strictly increasing ms
            last_ts = ts
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            lm = to_landmarks(landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts))
            now = time.monotonic()
            fps = 0.9 * fps + 0.1 / max(now - prev, 1e-6)
            prev = now
            draw(frame, lm, ["MODE: PREVIEW", f"FPS {fps:.0f}"])
            cv2.imshow("gesture-mouse", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
