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

    # Build scene assets, then validate/re-encode them with Pillow before FFmpeg.
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
            # If a provider returned non-image data, replace it with a known-good local visual.
            im=Image.new("RGB",(1080,1920),[(7,17,14),(12,30,24),(13,38,30)][i%3])
            d=ImageDraw.Draw(im)
            d.text((80,1490),str(q).upper()[:28],font=font(54),fill=(240,246,243))
            im.save(p,"JPEG",quality=92)
        scenes.append(p)

    poster=GEN/f"{video_id}.jpg"
    shutil.copyfile(scenes[0],poster)
    if not ff:
        return str(poster),None,"FFmpeg not installed; poster created."

    caption=GEN/f"{video_id}.ass"
    ass(idea.beats or [],caption)
    duration=max(10,float((idea.beats or [{"end":27}])[-1].get("end",27)))
    out=GEN/f"{video_id}.mp4"
    tmp=GEN/f"{video_id}.rendering.mp4"
    cap=str(caption).replace("\\","/").replace(":","\\:")

    # Single-pass render avoids corrupt intermediate MP4 segments and concat failures.
    cmd=[ff,"-y","-loop","1","-i",str(scenes[0]),"-i",str(voicep),
         "-vf",f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles='{cap}'",
         "-t",str(duration),"-r","30","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(tmp)]
    proc=subprocess.run(cmd,capture_output=True,text=True)
    if proc.returncode!=0 or not tmp.exists() or tmp.stat().st_size<1024:
        try: tmp.unlink()
        except: pass
        return str(poster),None,"FFmpeg render failed: "+proc.stderr[-1200:]
    tmp.replace(out)
    return str(poster),str(out),"Rendered voice + validated media + timed captions."
'''
p.write_text(head + new_render)
print('ThemeForge renderer patched: validated media + single-pass FFmpeg')
