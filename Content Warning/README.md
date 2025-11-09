## fake-but-native-ffmpeg.py

This is daemon, run ONLY on host OS
Listening on TCP port 33445 and waiting args from .exe stub
Uses GStreamer and VAAPI to encode video

## fake-ffmpeg.cpp

This is stub, aka fake ffmpeg, compile with `x86_64-w64-mingw32-g++ -O2 -static -s -o ffmpeg.exe fake-ffmpeg.cpp -lws2_32` and replace file `<gameroot>/Content Warning_Data/StreamingAssets/FFmpegOut/Windows/ffmpeg.exe` with it