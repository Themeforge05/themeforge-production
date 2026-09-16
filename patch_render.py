from pathlib import Path

p = Path('/app/app/media_factory.py')
s = p.read_text()
marker = 'async def render(video_id,idea):'
if marker not in s:
    raise SystemExit('render function not found')
head = s.split(marker, 1)[0]
new_render = r'''async def render(video_id,idea):
    ff=shutil.which("ffmpeg")
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
                clean.save(p,"JPEG",quality=92,optimize=True)
        except Exception:
            im=Image.new("RGB",(1080,1920),[(7,17,14),(12,30,24),(13,38,30)][i%3])
            d=ImageDraw.Draw(im)
            d.text((80,1490),str(q).upper()[:28],font=font(54),fill=(240,246,243))
            im.save(p,"JPEG",quality=92)
        scenes.append(p)

    poster=GEN/f"{video_id}.jpg"
    shutil.copyfile(scenes[0],poster)
    if not ff:
        return str(poster),None,"Render failed: FFmpeg is unavailable."

    caption=GEN/f"{video_id}.ass"
    ass(idea.beats or [],caption)
    duration=max(10.0,float((idea.beats or [{"end":27}])[-1].get("end",27)))
    out=GEN/f"{video_id}.mp4"
    tmp=GEN/f"{video_id}.rendering.mp4"
    cap=str(caption).replace("\\","/").replace(":","\\:")

    # Pad the voice track with silence so a zero/short TTS WAV cannot make -shortest
    # terminate the render at frame 0. The explicit -t is the sole duration authority.
    cmd=[ff,"-y","-loop","1","-framerate","30","-i",str(scenes[0]),"-i",str(voicep),
         "-vf",f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles='{cap}'",
         "-af",f"apad=pad_dur={duration}","-t",str(duration),"-r","30",
         "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
         "-c:a","aac","-ar","44100","-b:a","128k","-movflags","+faststart",str(tmp)]
    proc=subprocess.run(cmd,capture_output=True,text=True)
    if proc.returncode!=0 or not tmp.exists() or tmp.stat().st_size<4096:
        try: tmp.unlink()
        except: pass
        detail=(proc.stderr or "Unknown FFmpeg error")[-1600:]
        return str(poster),None,"Render failed: "+detail
    tmp.replace(out)
    return str(poster),str(out),"Rendered successfully. Preview the MP4 before approval."
'''
p.write_text(head + new_render)
print('ThemeForge renderer patched: padded audio + explicit duration + validated media')
