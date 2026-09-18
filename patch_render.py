from pathlib import Path

p = Path('/app/app/media_factory.py')
s = p.read_text()
marker = 'async def render(video_id,idea):'
if marker not in s:
    raise SystemExit('render function not found')
head = s.split(marker, 1)[0]
new_render = r'''async def render(video_id,idea):
    ff=shutil.which("ffmpeg")
    probe=shutil.which("ffprobe")
    voicep=GEN/f"{video_id}.wav"
    await voice(idea.script,voicep)

    scenes=[]
    for i,q in enumerate(idea.media_queries or ["vertical background"]):
        p=GEN/f"{video_id}_scene{i}.jpg"
        await scene(q,p,i)
        try:
            with Image.open(p) as im:
                im.load()
                clean=im.convert("RGB")
                clean.save(p,"JPEG",quality=92)
        except Exception:
            im=Image.new("RGB",(1080,1920),(12,30,24))
            d=ImageDraw.Draw(im)
            d.text((80,1490),str(q).upper()[:28],font=font(54),fill=(240,246,243))
            im.save(p,"JPEG",quality=92)
        scenes.append(p)

    poster=GEN/f"{video_id}.jpg"
    shutil.copyfile(scenes[0],poster)
    if not ff:
        return str(poster),None,"Render failed: FFmpeg unavailable."

    duration=max(10.0,float((idea.beats or [{"end":20}])[-1].get("end",20)))
    out=GEN/f"{video_id}.mp4"
    silent=GEN/f"{video_id}.video.mp4"
    finaltmp=GEN/f"{video_id}.rendering.mp4"

    # Stage 1: create a known-good video stream only. No subtitles/audio/filter complexity.
    cmd1=[ff,"-y","-loop","1","-framerate","30","-i",str(scenes[0]),
          "-t",str(duration),"-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
          "-r","30","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",
          "-movflags","+faststart","-an",str(silent)]
    a=subprocess.run(cmd1,capture_output=True,text=True,timeout=120)
    if a.returncode!=0 or not silent.exists() or silent.stat().st_size<4096:
        detail=(a.stderr or "video stage failed")[-1200:]
        return str(poster),None,"Render failed (video stage): "+detail

    # Stage 2: mux voiceover. apad + explicit duration makes short/empty-tail audio harmless.
    cmd2=[ff,"-y","-i",str(silent),"-i",str(voicep),
          "-filter_complex",f"[1:a]apad=pad_dur={duration}[a]",
          "-map","0:v:0","-map","[a]","-t",str(duration),
          "-c:v","copy","-c:a","aac","-ar","44100","-b:a","128k",
          "-movflags","+faststart",str(finaltmp)]
    b=subprocess.run(cmd2,capture_output=True,text=True,timeout=120)
    if b.returncode!=0 or not finaltmp.exists() or finaltmp.stat().st_size<4096:
        detail=(b.stderr or "audio mux stage failed")[-1200:]
        return str(poster),None,"Render failed (audio stage): "+detail

    # Validate that ffprobe sees a positive-duration video stream before approval.
    if probe:
        q=subprocess.run([probe,"-v","error","-select_streams","v:0","-show_entries",
                          "stream=duration","-of","default=noprint_wrappers=1:nokey=1",str(finaltmp)],
                         capture_output=True,text=True,timeout=30)
        try:
            valid=float((q.stdout or "0").strip())>0
        except Exception:
            valid=False
        if not valid:
            return str(poster),None,"Render failed validation: MP4 has no playable video duration."

    finaltmp.replace(out)
    try: silent.unlink()
    except: pass
    return str(poster),str(out),"Rendered successfully. Preview the MP4 before approval."
'''
p.write_text(head + new_render)
print('ThemeForge renderer patched: two-stage reliable MP4 pipeline')
