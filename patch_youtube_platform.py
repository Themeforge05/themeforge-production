from pathlib import Path

root=Path('/app')
models=root/'app/models.py';main=root/'app/main.py';html=root/'app/static/index.html';yt=root/'app/youtube.py'

yt.write_text(r'''from __future__ import annotations
import os
from pathlib import Path
from urllib.parse import urlencode
import httpx
AUTH="https://accounts.google.com/o/oauth2/v2/auth";TOKEN="https://oauth2.googleapis.com/token"
UPLOAD="https://www.googleapis.com/upload/youtube/v3/videos";SCOPE="https://www.googleapis.com/auth/youtube.upload"
def redirect_uri():return os.getenv("YOUTUBE_REDIRECT_URI") or os.getenv("APP_URL","").rstrip("/")+"/api/youtube/callback"
def configured():return bool(os.getenv("YOUTUBE_CLIENT_ID") and os.getenv("YOUTUBE_CLIENT_SECRET") and redirect_uri())
def auth_url(state:str):
    if not configured():raise RuntimeError("YouTube OAuth is not configured")
    return AUTH+"?"+urlencode({"client_id":os.getenv("YOUTUBE_CLIENT_ID"),"redirect_uri":redirect_uri(),"response_type":"code","scope":SCOPE,"access_type":"offline","prompt":"consent","include_granted_scopes":"true","state":state})
async def exchange(code:str):
    async with httpx.AsyncClient(timeout=60) as c:
        r=await c.post(TOKEN,data={"client_id":os.getenv("YOUTUBE_CLIENT_ID"),"client_secret":os.getenv("YOUTUBE_CLIENT_SECRET"),"code":code,"grant_type":"authorization_code","redirect_uri":redirect_uri()});r.raise_for_status();return r.json()
async def refresh(refresh_token:str):
    async with httpx.AsyncClient(timeout=60) as c:
        r=await c.post(TOKEN,data={"client_id":os.getenv("YOUTUBE_CLIENT_ID"),"client_secret":os.getenv("YOUTUBE_CLIENT_SECRET"),"refresh_token":refresh_token,"grant_type":"refresh_token"});r.raise_for_status();return r.json()
async def upload(path:Path,access_token:str,title:str,description:str,privacy:str="private"):
    metadata={"snippet":{"title":title[:100],"description":description[:5000]},"status":{"privacyStatus":privacy,"selfDeclaredMadeForKids":False}}
    headers={"Authorization":f"Bearer {access_token}","Content-Type":"application/json; charset=UTF-8","X-Upload-Content-Type":"video/mp4","X-Upload-Content-Length":str(path.stat().st_size)}
    async with httpx.AsyncClient(timeout=300,follow_redirects=True) as c:
        start=await c.post(UPLOAD,params={"uploadType":"resumable","part":"snippet,status","notifySubscribers":"false"},headers=headers,json=metadata);start.raise_for_status()
        location=start.headers.get("Location")
        if not location:raise RuntimeError("YouTube did not start a resumable upload")
        sent=await c.put(location,headers={"Authorization":f"Bearer {access_token}","Content-Type":"video/mp4"},content=path.read_bytes());sent.raise_for_status();return sent.json()
''')

m=models.read_text()
if 'youtube = relationship("YouTubeConnection"' not in m:
    anchor='    instagram = relationship("InstagramConnection", back_populates="owner", uselist=False, cascade="all,delete-orphan")'
    if anchor in m:m=m.replace(anchor,anchor+'\n    youtube = relationship("YouTubeConnection", back_populates="owner", uselist=False, cascade="all,delete-orphan")')
    else:
        anchor='    tiktok = relationship("TikTokConnection", back_populates="owner", uselist=False, cascade="all,delete-orphan")'
        m=m.replace(anchor,anchor+'\n    youtube = relationship("YouTubeConnection", back_populates="owner", uselist=False, cascade="all,delete-orphan")')
if 'class YouTubeConnection' not in m:
    m += '''

class YouTubeConnection(Base):
    __tablename__="youtube_connections"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[int|None] = mapped_column(Integer, nullable=True)
    owner = relationship("User", back_populates="youtube")

class YouTubePublish(Base):
    __tablename__="youtube_publishes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)
    youtube_video_id: Mapped[str] = mapped_column(String(120))
    privacy: Mapped[str] = mapped_column(String(30), default="private")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
'''
models.write_text(m)

s=main.read_text()
s=s.replace('from . import tiktok,instagram','from . import tiktok,instagram,youtube').replace('from . import tiktok\n','from . import tiktok,youtube\n')
s=s.replace('"tiktok_connected":u.tiktok is not None','"tiktok_connected":u.tiktok is not None,"youtube_connected":u.youtube is not None,"youtube_configured":youtube.configured()')
if '/api/youtube/connect' not in s:
    s += r'''

youtube_oauth_states={}
@app.get("/api/youtube/connect")
def youtube_connect(u:User=Depends(current_user)):
    if not youtube.configured():raise HTTPException(503,"YouTube OAuth credentials have not been configured")
    state=secrets.token_urlsafe(24);youtube_oauth_states[state]=u.id
    return {"url":youtube.auth_url(state)}

@app.get("/api/youtube/callback")
async def youtube_callback(code:str,state:str,db:Session=Depends(get_db)):
    import time
    uid=youtube_oauth_states.pop(state,None)
    if not uid:raise HTTPException(400,"Invalid YouTube OAuth state")
    try:data=await youtube.exchange(code)
    except Exception as e:raise HTTPException(400,f"YouTube connection failed: {e}")
    c=db.scalar(select(YouTubeConnection).where(YouTubeConnection.user_id==uid))
    if not c:c=YouTubeConnection(user_id=uid,access_token="");db.add(c)
    c.access_token=data["access_token"]
    if data.get("refresh_token"):c.refresh_token=data["refresh_token"]
    c.expires_at=int(time.time())+int(data.get("expires_in",3600));db.commit()
    return RedirectResponse("/?youtube=connected")

@app.post("/api/videos/{vid}/youtube")
async def youtube_publish(vid:int,privacy:str="private",u:User=Depends(current_user),db:Session=Depends(get_db)):
    import time
    if not u.youtube:raise HTTPException(400,"YouTube is not connected")
    if privacy not in ("private","unlisted","public"):raise HTTPException(400,"Invalid YouTube privacy setting")
    v=db.scalar(select(Video).where(Video.id==vid,Video.user_id==u.id))
    if not v or v.status!="approved" or not v.video_path:raise HTTPException(400,"Approve a playable MP4 first")
    if not u.youtube.refresh_token:raise HTTPException(400,"Reconnect YouTube to grant offline upload access")
    try:
        token=await youtube.refresh(u.youtube.refresh_token);u.youtube.access_token=token["access_token"];u.youtube.expires_at=int(time.time())+int(token.get("expires_in",3600));db.commit()
        idea=db.get(Idea,v.idea_id)
        result=await youtube.upload(ROOT/"storage"/"generated"/Path(v.video_path).name,u.youtube.access_token,idea.title or idea.hook,idea.caption,privacy)
        yid=str(result.get("id") or "")
        if not yid:raise RuntimeError("YouTube did not return a video ID")
        db.add(YouTubePublish(user_id=u.id,video_id=v.id,youtube_video_id=yid,privacy=privacy));v.status="uploaded_youtube";db.commit()
        return {"status":"uploaded","video_id":yid,"url":"https://www.youtube.com/watch?v="+yid,"privacy":privacy}
    except HTTPException:raise
    except Exception as e:raise HTTPException(400,f"YouTube upload failed: {e}")
'''
main.write_text(s)

h=html.read_text();import re
h=h.replace('Instagram/TikTok publishing','Instagram/YouTube publishing').replace('TikTok export','YouTube publishing')
h=re.sub(r'<div class="card"><h2>TikTok</h2>.*?</div>','',h,count=1,flags=re.S)
youtube_card='<div class="card"><h2>YouTube Shorts</h2><p id="ytstate" class="muted"></p><button class="btn g" onclick="connectYouTube()">Connect YouTube</button><p class="muted">Approved vertical videos can be uploaded directly to your YouTube channel.</p></div>'
h=h.replace('<div class="card"><h2>OpenAI + media</h2>',youtube_card+'<div class="card"><h2>Cloud Video</h2>')
h=re.sub(r'async function connectTikTok\(\).*?async function render\(\)', 'async function render()',h,count=1,flags=re.S)
functions='async function connectYouTube(){try{let x=await A("/api/youtube/connect");location.href=x.url}catch(e){alert(e.message)}}\nasync function ytPost(id){let privacy=prompt("YouTube privacy: private, unlisted, or public","private")||"private";if(!confirm("Upload this approved video to YouTube as "+privacy+"?"))return;try{let x=await A("/api/videos/"+id+"/youtube?privacy="+privacy,{method:"POST"});alert("Uploaded to YouTube: "+x.url);load()}catch(e){alert(e.message)}}\n'
h=h.replace('async function render(){',functions+'async function render(){')
h=h.replace('$(\"ttstate\").textContent=S.tiktok_connected?\"TikTok connected.\":\"TikTok not connected.\";','$(\"ytstate\").textContent=S.youtube_connected?\"YouTube connected.\":(S.youtube_configured?\"YouTube ready to connect.\":\"YouTube API setup required.\");')
h=re.sub(r'<button class="btn" onclick="tt\(\$\{v.id\},\'draft\'\)">TikTok Draft</button><button class="btn" onclick="tt\(\$\{v.id\},\'direct\'\)">Direct Post</button>','<button class="btn g" onclick="ytPost(${v.id})">Upload YouTube Short</button>',h)
if 'Upload YouTube Short' not in h:
    h=h.replace('<button class="btn g" onclick="igPost(${v.id})">Post Instagram Reel</button>','<button class="btn g" onclick="igPost(${v.id})">Post Instagram Reel</button><button class="btn g" onclick="ytPost(${v.id})">Upload YouTube Short</button>')
html.write_text(h)
print('ThemeForge YouTube integration installed and TikTok removed from the workflow')
