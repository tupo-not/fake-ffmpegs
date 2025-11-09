import os, sys, socket, shlex, subprocess
from os import getenv, system

CW_DRIVEC = os.getenv("CW_COMPATDATA_DRIVEC")
if not CW_DRIVEC:
    raise RuntimeError("CW_COMPATDATA_DRIVEC not set — cannot fix Windows paths")

HOST, PORT = "127.0.0.1", 33445

def log(msg): print(msg)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((HOST, PORT))
sock.listen(1)
log(f"[daemon] listening {HOST}:{PORT}")

while True:
    conn, addr = sock.accept()
    data = b""
    while True:
        chunk = conn.recv(4096)
        if not chunk: break
        data += chunk

    if not data:
        conn.close()
        continue

    try:
        raw_text = data.decode("utf-8", errors="replace")
        log(f"[daemon] got raw: {raw_text}")

        argv = raw_text.strip().split(" ")

        def fix_path(arg):
            if len(arg) > 2 and arg[1] == ":" and arg[0].isalpha():
                drive = arg[0].lower()
                rest = arg[2:].replace("\\", "/")
                if drive != "c":
                    raise RuntimeError(f"Unexpected drive '{drive}' in path: {arg}")
                return os.path.join(CW_DRIVEC, rest.lstrip("/"))
            return arg

        argv = [fix_path(a) for a in argv]
        log(f"[daemon] fixed argv: {argv}")

    except Exception as e:
        log(f"[daemon] bad args: {e}")
        conn.close()
        continue

    fps = frames_path = audio_path = mic_path = out_path = None
    for i,a in enumerate(argv):
        la = a.lower()
        if a == "-r" and i+1 < len(argv): fps = argv[i+1]
        elif ".png" in la and "%04d" in la: frames_path = a
        elif la.endswith("audio.raw"): audio_path = a
        elif la.endswith("mic.raw"): mic_path = a
        elif la.endswith(".webm") or la.endswith(".mp4"): out_path = a

    if not all([frames_path,audio_path,mic_path,out_path]):
        log("Missing paths, skipping")
        conn.close()
        continue

    for src in [(audio_path,2),(mic_path,1)]:
        p = subprocess.run(["ffmpeg","-hide_banner","-f","f32le","-ac",str(src[1]),"-ar","48000",
                            "-i",src[0],"-ar","48000","-ac","2","-sample_fmt","s16",
                            f"{src[0]}.wav"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log(p.stdout)

    import gi
    gi.require_version("Gst","1.0")
    from gi.repository import Gst, GLib
    Gst.init(None)

    pipeline = Gst.Pipeline.new("fake_ffmpeg")
    pic_src = Gst.ElementFactory.make("multifilesrc","pic_src")
    pngdec = Gst.ElementFactory.make("pngdec","pngdec")
    videoconvertscale = Gst.ElementFactory.make("videoconvertscale","videoconvertscale")
    capsfilter = Gst.ElementFactory.make("capsfilter","capsfilter")
    vaapih264enc = Gst.ElementFactory.make("vaapih264enc","vaapih264enc")
    h264parse = Gst.ElementFactory.make("h264parse","h264parse")
    mp4mux = Gst.ElementFactory.make("mp4mux","mp4mux")
    mp4sink = Gst.ElementFactory.make("filesink","mp4sink")
    wav_src = Gst.ElementFactory.make("filesrc","wav_src")
    wavparse = Gst.ElementFactory.make("wavparse","wavparse")
    audioconvert = Gst.ElementFactory.make("audioconvert","audioconvert")
    audioresample = Gst.ElementFactory.make("audioresample","audioresample")
    aac_enc = Gst.ElementFactory.make("avenc_aac","aac_enc")

    capsfilter.set_property("caps",Gst.Caps.from_string("video/x-raw,format=NV12"))
    mp4mux.set_property("faststart",True)
    mp4sink.set_property("location",out_path)
    pic_src.set_property("location",frames_path)
    pic_src.set_property("caps",Gst.Caps.from_string(f"image/png,framerate={fps}/1"))
    wav_src.set_property("location",f"{audio_path}.wav")

    for el in [pic_src,pngdec,videoconvertscale,capsfilter,vaapih264enc,h264parse,mp4mux,mp4sink,
               wav_src,audioconvert,audioresample,wavparse,aac_enc]:
        pipeline.add(el)
    pic_src.link(pngdec)
    pngdec.link(videoconvertscale)
    videoconvertscale.link(capsfilter)
    capsfilter.link(vaapih264enc)
    vaapih264enc.link(h264parse)
    h264parse.link(mp4mux)
    mp4mux.link(mp4sink)
    wav_src.link(wavparse)
    wavparse.link(audioconvert)
    audioconvert.link(audioresample)
    audioresample.link(aac_enc)
    aac_enc.link(mp4mux)

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    loop = GLib.MainLoop()
    def on_message(bus,message,loop=loop):
        t = message.type
        if t == Gst.MessageType.EOS or t == Gst.MessageType.ERROR:
            loop.quit()
        return True
    bus.connect("message",on_message)
    pipeline.set_state(Gst.State.PLAYING)
    loop.run()

    try:
        system(f"cp {out_path} /home/tupo-nain/Desktop/out.mp4 -f")
        conn.sendall(b"now u can crash UwU")
        log("sent 'DONE'")
        from shutil import rmtree
        from os import remove
        remove(f"{audio_path}")
        remove(f"{mic_path}")
        remove(f"{audio_path}.wav")
        remove(f"{mic_path}.wav")
    except Exception as e:
        log(f"[daemon] failed to send DONE: {e}")
    conn.close()
