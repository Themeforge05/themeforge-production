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

    queries=list(idea.media_queries or [])
    if len(queries)<3:
        fallback=[getattr(idea,"hook",""), getattr(idea,"title",""), getattr(idea,"script","")[:140], "vertical cinematic background"]
        queries.extend([str(x) for x in fallback if x and str(x) not in queries])
    queries=queries[:8]

    scenes=[]
    for i,q in enumerate(queries):
        scene_path=GEN/f"{video_id}_scene{i}.jpg"
        await scene(q,scene_path,i)
        try:
            with Image.open(scene_path) as source:
                source.load()
                clean=source.convert("RGB")
                clean.save(scene_path,"JPEG",quality=92)
        except Exception:
            fallback_image=Image.new("RGB",(1080,1920),(12,30,24))
            draw=ImageDraw.Draw(fallback_image)
            draw.text((80,1490),str(q).upper()[:28],font=font(54),fill=(240,246,243))
            fallback_image.save(scene_path,"JPEG",quality=92)
        scenes.append(scene_path)

    poster=GEN/f"{video_id}.jpg"
    shutil.copyfile(scenes[0],poster)
    if not ff:
        return str(poster),None,"Render failed: FFmpeg unavailable."

    def media_duration(path):
        if not probe or not path.exists(): return 0.0
        result=subprocess.run([probe,"-v","error","-show_entries","format=duration",
            "-of","default=noprint_wrappers=1:nokey=1",str(path)],capture_output=True,text=True,timeout=30)
        try: return max(0.0,float((result.stdout or "0").strip()))
        except Exception: return 0.0

    beats=list(idea.beats or [])
    beat_end=max([float(b.get("end",0) or 0) for b in beats] or [0])
    voice_duration=media_duration(voicep)
    # Social videos should not collapse to a 20-second placeholder. Use the full narration,
    # honor longer beat timing, and provide a useful minimum without exceeding 90 seconds.
    duration=min(90.0,max(45.0,beat_end,voice_duration))
    segment=duration/len(scenes)
    out=GEN/f"{video_id}.mp4"
    concat_file=GEN/f"{video_id}_scenes.txt"
    silent=GEN/f"{video_id}.video.mp4"
    finaltmp=GEN/f"{video_id}.rendering.mp4"

    # Animate every generated scene with a gentle alternating Ken Burns move, then concatenate.
    clips=[]
    for i,scene_path in enumerate(scenes):
        clip=GEN/f"{video_id}_clip{i}.mp4"
        zoom="min(zoom+0.0007,1.10)" if i%2==0 else "if(eq(on,1),1.10,max(zoom-0.0007,1.0))"
        vf=("scale=1200:2134:force_original_aspect_ratio=increase,"
            "crop=1200:2134,zoompan=z='"+zoom+"':"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
            "format=yuv420p")
        cmd=[ff,"-y","-loop","1","-framerate","30","-i",str(scene_path),"-t",str(segment),
             "-vf",vf,"-r","30","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
             "-movflags","+faststart","-an",str(clip)]
        run=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
        if run.returncode!=0 or not clip.exists() or clip.stat().st_size<4096:
            detail=(run.stderr or "scene animation failed")[-1200:]
            return str(poster),None,"Render failed (scene stage): "+detail
        clips.append(clip)

    concat_file.write_text("".join("file '"+str(c).replace("'","'\\''")+"'\n" for c in clips))
    joined=subprocess.run([ff,"-y","-f","concat","-safe","0","-i",str(concat_file),
        "-c","copy","-movflags","+faststart",str(silent)],capture_output=True,text=True,timeout=180)
    if joined.returncode!=0 or not silent.exists() or silent.stat().st_size<4096:
        detail=(joined.stderr or "scene join failed")[-1200:]
        return str(poster),None,"Render failed (join stage): "+detail

    # Mux narration; preserve the visual duration and pad only the tail when narration is shorter.
    mux=subprocess.run([ff,"-y","-i",str(silent),"-i",str(voicep),
        "-filter_complex",f"[1:a]apad=pad_dur={duration}[a]","-map","0:v:0","-map","[a]",
        "-t",str(duration),"-c:v","copy","-c:a","aac","-ar","44100","-b:a","128k",
        "-movflags","+faststart",str(finaltmp)],capture_output=True,text=True,timeout=180)
    if mux.returncode!=0 or not finaltmp.exists() or finaltmp.stat().st_size<4096:
        detail=(mux.stderr or "audio mux failed")[-1200:]
        return str(poster),None,"Render failed (audio stage): "+detail

    if probe:
        check=subprocess.run([probe,"-v","error","-select_streams","v:0","-show_entries",
            "stream=duration","-of","default=noprint_wrappers=1:nokey=1",str(finaltmp)],
            capture_output=True,text=True,timeout=30)
        try: valid=float((check.stdout or "0").strip())>=duration-1
        except Exception: valid=False
        if not valid:
            return str(poster),None,"Render failed validation: MP4 duration is incomplete."

    finaltmp.replace(out)
    for temp in clips+[silent,concat_file]:
        try: temp.unlink()
        except Exception: pass
    return str(poster),str(out),f"Rendered successfully: {len(scenes)} animated scenes, {duration:.0f} seconds. Preview before approval."
'''
p.write_text(head + new_render)
print('ThemeForge renderer patched: animated multi-scene MP4 pipeline')
