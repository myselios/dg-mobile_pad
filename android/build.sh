#!/bin/bash
# Builds build/trackpad.apk without Gradle. Runs inside the Dockerfile image.
set -euo pipefail
BT=$ANDROID_HOME/build-tools/34.0.0
JAR=$ANDROID_HOME/platforms/android-34/android.jar
rm -rf build && mkdir -p build/classes build/test build/dex
# Unit tests for the pure-Java parts (no Android needed).
javac -d build/test src/local/trackpad/Hid.java test/*.java
java -ea -cp build/test HidTest
javac --release 11 -cp "$JAR" -d build/classes $(find src -name '*.java')
"$BT/d8" --lib "$JAR" --min-api 28 --output build/dex $(find build/classes -name '*.class')
"$BT/aapt2" link -o build/base.apk --manifest AndroidManifest.xml -I "$JAR" --min-sdk-version 28 --target-sdk-version 34
(cd build/dex && zip -q ../base.apk classes.dex)
"$BT/zipalign" -f 4 build/base.apk build/aligned.apk
[ -f debug.keystore ] || keytool -genkeypair -keystore debug.keystore -storepass android -keypass android \
  -alias debug -keyalg RSA -validity 10000 -dname "CN=debug" >/dev/null 2>&1
"$BT/apksigner" sign --ks debug.keystore --ks-pass pass:android --out build/trackpad.apk build/aligned.apk
echo "OK: build/trackpad.apk"
