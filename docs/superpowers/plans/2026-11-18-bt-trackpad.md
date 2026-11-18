# Bluetooth Trackpad (Android app) Plan

**Goal:** A Galaxy phone works as a Bluetooth mouse for a MacBook and a Galaxy Tab, with nothing installed on either.

**Architecture:** A native Android app (Java, no Gradle). It registers as a Bluetooth HID device through `BluetoothHidDevice`, which needs API 28 or later, and sends mouse reports. The host sees an ordinary BT mouse. It is built in Docker (`android/Dockerfile`, linux/amd64) with javac, d8, aapt2 and apksigner. The APK is installed by downloading it on the phone over the LAN.

**Safety:**
- Sending only happens while a host is connected.
- On touch cancel, the app sends "button up".
- When the BT link drops, the host releases the button.
- When the app closes, it unregisters.

## Stages
1. **Feasibility (this stage):** pair, connect, one-finger move, tap to click. Pure report encoding (`Hid.java`) is unit-tested in the Docker build. It is verified on the user's own phone with their own Mac, then on the wife's Galaxy phone with her MacBook and Galaxy Tab.
2. **Trackpad parity:**
   - Gestures: double-tap drag, two-finger scroll (wheel), two-finger right-click, ON/OFF.
   - The touch logic is a pure class with tests.
3. **Host switcher and YouTube keys:**
   - Switch between MacBook and Tab.
   - Add a combo keyboard descriptor with the keys Shift+N, Shift+P, K and `/`.

## Build / install
- `docker build --platform linux/amd64 -t trackpad-build android && docker run --rm --platform linux/amd64 -v "$PWD/android":/app trackpad-build ./build.sh`
- Result: `android/build/trackpad.apk`. The debug keystore, `android/debug.keystore`, is git-ignored and kept so that updates install over the old version.
