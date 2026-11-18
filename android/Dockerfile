# Android build tools ship as x86_64 Linux binaries, hence linux/amd64 (runs under Rosetta on Apple silicon).
FROM --platform=linux/amd64 eclipse-temurin:17-jdk
RUN apt-get update && apt-get install -y --no-install-recommends unzip zip curl && rm -rf /var/lib/apt/lists/*
ENV ANDROID_HOME=/opt/android
RUN curl -fsSL -o /tmp/t.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip \
 && mkdir -p $ANDROID_HOME/cmdline-tools && unzip -q /tmp/t.zip -d $ANDROID_HOME/cmdline-tools \
 && mv $ANDROID_HOME/cmdline-tools/cmdline-tools $ANDROID_HOME/cmdline-tools/latest && rm /tmp/t.zip
RUN yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses >/dev/null \
 && $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "platforms;android-34" "build-tools;34.0.0" >/dev/null
WORKDIR /app
