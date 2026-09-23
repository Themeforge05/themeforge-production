from pathlib import Path

root=Path('/app')
cloud=root/'app/cloud_media.py'
main=root/'app/main.py'

cloud.write_text(r'''from __future__ import annotations
import asyncio, os, shutil, subprocess
from pathlib import Path
import httpx
from runwayml import RunwayML
from .media_factory import voice

ROOT=Path(__file__).resolve().parent.parent
GEN=ROOT/'storage'/'generated'
GEN.mkdir(parents=True,exist_ok=True)

def configuration():
    return {
        "runway":bool(os.getenv("RUNWAY_API_KEY") or os.getenv("RUNWAYML_API_SECRET")),
        "creatomate":bool(os.getenv("CREATOMATE_API_KEY")),
        "template":bool(os.getenv("CREATOMATE_TEMPLATE_ID")),
        "public_url":bool(os.getenv("APP_URL")),
    }

def configured():
    return all(configuration().values())

def _runway_clip(prompt:str):
    key=os.getenv("RUNWAY_API_KEY") or os.getenv("RUNWAYML_API_SECRET")
    client=RunwayML(api_key=key)
    task=client.image_to_video.create(
        model=os.getenv("RUNWAY_VIDEO_MODEL","gen4.5"),
        prompt_text=prompt,
        ratio=os.getenv("RUNWAY_VIDEO_RATIO","720:1280"),
        duration=int(os.getenv("RUNWAY_CLIP_SECONDS","5")),
    ).wait_for_task_output()
    outputs=getattr(task,"output",None) or []
    if not outputs: raise RuntimeError("Runway completed without returning a video URL")
    return outputs[0]

async def _creatomate_render(modifications:dict):
    key=os.getenv("CREATOMATE_API_KEY","")
    template=os.getenv("CREATOMATE_TEMPLATE_ID","")
    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}
    async with httpx.AsyncClient(timeout=120) as c:
        r=await c.post("https://api.creatomate.com/v2/renders",headers=headers,json={
            "template_id":template,"modifications":modifications,
        })
        r.raise_for_status()
        data=r.json();job=data[0] if isinstance(data,list) else data
        rid=job.get("id")
        if not rid: raise RuntimeError("Creatomate did not return a render ID")
        for _ in range(120):
            await asyncio.sleep(3)
            status=await c.get(f"https://api.creatomate.com/v2/renders/{rid}",headers=headers)
            status.raise_for_status();job=status.json()
            state=str(job.get("status","")).lower()
            if state=="succeeded" and job.get("url"): return job["url"]
            if state in ("failed","error"): raise RuntimeError("Creatomate render failed: "+str(job.get("error_message") or job))
    raise RuntimeError("Creatomate render did not finish within six minutes")

async def render(video_id,idea):
    cfg=configuration();missing=[name for name,ok in cfg.items() if not ok]
    if missing: raise RuntimeError("Cloud video setup required: "+", ".join(missing))
    count=max(3,min(5,int(os.getenv("RUNWAY_SCENE_COUNT","4"))))
    raw=list(idea.media_queries or [])
    seeds=(raw+[idea.hook,idea.title,idea.script])[:count]
    prompts=[str(seed)+". Cinematic vertical social video, realistic motion, strong visual storytelling, no captions, no logos, no watermark, 9:16 composition." for seed in seeds]
    while len(prompts)<count: prompts.append(prompts[-1])
    clip_urls=[]
    for prompt in prompts: clip_urls.append(await asyncio.to_thread(_runway_clip,prompt))

    voice_path=GEN/f"{video_id}_voice.wav"
    await voice(idea.script,voice_path)
    public=os.getenv("APP_URL","").rstrip("/")
    modifications={"Hook.text":idea.hook,"Title.text":idea.title,"Voiceover.source":public+"/generated/"+voice_path.name}
    for n,url in enumerate(clip_urls,1): modifications[f"Video-{n}.source"]=url
    for n,beat in enumerate(list(idea.beats or [])[:8],1): modifications[f"Caption-{n}.text"]=str(beat.get("text",""))

    result_url=await _creatomate_render(modifications)
    out=GEN/f"{video_id}.mp4"
    async with httpx.AsyncClient(timeout=300,follow_redirects=True) as c:
        r=await c.get(result_url);r.raise_for_status();out.write_bytes(r.content)
    if out.stat().st_size<100000: raise RuntimeError("Creatomate returned an incomplete MP4")
    poster=GEN/f"{video_id}.jpg";ff=shutil.which("ffmpeg")
    if ff: subprocess.run([ff,"-y","-ss","0.5","-i",str(out),"-frames:v","1","-q:v","2",str(poster)],capture_output=True,timeout=60)
    if not poster.exists():
        from PIL import Image,ImageDraw
        im=Image.new("RGB",(720,1280),(8,22,17));ImageDraw.Draw(im).text((50,1050),str(idea.hook)[:50],fill=(240,246,243));im.save(poster,"JPEG",quality=90)
    return str(poster),str(out),f"Cloud render complete: {len(clip_urls)} Runway scenes assembled by Creatomate."
''')

s=main.read_text()
s=s.replace('from .media_factory import render','from .cloud_media import render')
if 'from . import cloud_media' not in s:s=s.replace('from .revenue import economics,decide','from .revenue import economics,decide\nfrom . import cloud_media')
s=s.replace('"tiktok_connected":u.tiktok is not None','"tiktok_connected":u.tiktok is not None,"cloud_video_configured":cloud_media.configured(),"cloud_video_setup":cloud_media.configuration()')
main.write_text(s)
print('ThemeForge cloud video pipeline installed')
