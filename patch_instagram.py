from pathlib import Path

root=Path('/app')
models=root/'app/models.py'
main=root/'app/main.py'
html=root/'app/static/index.html'
ig=root/'app/instagram.py'

ig.write_text('''from __future__ import annotations
import os
from urllib.parse import urlencode
import httpx

AUTH='https://www.instagram.com/oauth/authorize'
TOKEN='https://api.instagram.com/oauth/access_token'
GRAPH='https://graph.instagram.com'
VERSION=os.getenv('META_GRAPH_VERSION','v26.0')
CLIENT_ID=os.getenv('INSTAGRAM_CLIENT_ID','')
CLIENT_SECRET=os.getenv('INSTAGRAM_CLIENT_SECRET','')
REDIRECT=os.getenv('INSTAGRAM_REDIRECT_URI','')
SCOPES='instagram_business_basic,instagram_business_content_publish'

def configured():
    return bool(CLIENT_ID and CLIENT_SECRET and REDIRECT)

def auth_url(state:str):
    if not configured(): raise RuntimeError('Instagram API is not configured yet')
    q=urlencode({'enable_fb_login':'0','force_authentication':'1','client_id':CLIENT_ID,'redirect_uri':REDIRECT,'response_type':'code','scope':SCOPES,'state':state})
    return AUTH+'?'+q

async def exchange(code:str):
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.post(TOKEN,data={'client_id':CLIENT_ID,'client_secret':CLIENT_SECRET,'grant_type':'authorization_code','redirect_uri':REDIRECT,'code':code})
        r.raise_for_status(); short=r.json()
        r=await c.get(GRAPH+'/access_token',params={'grant_type':'ig_exchange_token','client_secret':CLIENT_SECRET,'access_token':short['access_token']})
        r.raise_for_status(); long=r.json()
        tok=long['access_token']
        r=await c.get(f'{GRAPH}/{VERSION}/me',params={'fields':'user_id,username,account_type,profile_picture_url','access_token':tok})
        r.raise_for_status(); profile=r.json()
        return {'access_token':tok,'expires_in':long.get('expires_in'),'profile':profile}

async def profile(access_token:str):
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.get(f'{GRAPH}/{VERSION}/me',params={'fields':'user_id,username,account_type,profile_picture_url','access_token':access_token})
        r.raise_for_status(); return r.json()

async def create_reel(access_token:str,ig_user_id:str,video_url:str,caption:str):
    async with httpx.AsyncClient(timeout=60) as c:
        r=await c.post(f'{GRAPH}/{VERSION}/{ig_user_id}/media',data={'media_type':'REELS','video_url':video_url,'caption':caption[:2200],'share_to_feed':'true','access_token':access_token})
        r.raise_for_status(); return r.json()

async def container_status(access_token:str,container_id:str):
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.get(f'{GRAPH}/{VERSION}/{container_id}',params={'fields':'status_code,status','access_token':access_token})
        r.raise_for_status(); return r.json()

async def publish(access_token:str,ig_user_id:str,container_id:str):
    async with httpx.AsyncClient(timeout=60) as c:
        r=await c.post(f'{GRAPH}/{VERSION}/{ig_user_id}/media_publish',data={'creation_id':container_id,'access_token':access_token})
        r.raise_for_status(); return r.json()
''')

m=models.read_text()
m=m.replace('    tiktok = relationship("TikTokConnection", back_populates="owner", uselist=False, cascade="all,delete-orphan")','    tiktok = relationship("TikTokConnection", back_populates="owner", uselist=False, cascade="all,delete-orphan")\n    instagram = relationship("InstagramConnection", back_populates="owner", uselist=False, cascade="all,delete-orphan")')
if 'class InstagramConnection' not in m:
    m += '''\n\nclass InstagramConnection(Base):\n    __tablename__="instagram_connections"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)\n    access_token: Mapped[str] = mapped_column(Text)\n    ig_user_id: Mapped[str] = mapped_column(String(120))\n    username: Mapped[str] = mapped_column(String(180), default="")\n    account_type: Mapped[str] = mapped_column(String(60), default="")\n    expires_in: Mapped[int|None] = mapped_column(Integer, nullable=True)\n    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)\n    owner = relationship("User", back_populates="instagram")\n\nclass InstagramPublish(Base):\n    __tablename__="instagram_publishes"\n    id: Mapped[int] = mapped_column(primary_key=True)\n    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)\n    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)\n    container_id: Mapped[str] = mapped_column(String(120))\n    media_id: Mapped[str|None] = mapped_column(String(120), nullable=True)\n    status: Mapped[str] = mapped_column(String(40), default="processing")\n    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)\n'''
models.write_text(m)

s=main.read_text()
s=s.replace('from . import tiktok','from . import tiktok,instagram')
s=s.replace('"tiktok_connected":u.tiktok is not None}','"tiktok_connected":u.tiktok is not None,"instagram_connected":u.instagram is not None,"instagram_configured":instagram.configured()}')
if '/api/instagram/connect' not in s:
    s += '''\n\ninstagram_oauth_states={}\n@app.get("/api/instagram/connect")\ndef ig_connect(u:User=Depends(current_user)):\n    if not instagram.configured():raise HTTPException(503,"Instagram API credentials have not been configured in ThemeForge yet")\n    state=secrets.token_urlsafe(24);instagram_oauth_states[state]=u.id\n    return {"url":instagram.auth_url(state)}\n\n@app.get("/api/instagram/callback")\nasync def ig_callback(code:str,state:str,db:Session=Depends(get_db)):\n    uid=instagram_oauth_states.pop(state,None)\n    if not uid:raise HTTPException(400,"Invalid Instagram OAuth state")\n    try:data=await instagram.exchange(code)\n    except Exception as e:raise HTTPException(400,f"Instagram connection failed: {e}")\n    p=data.get("profile") or {}; igid=str(p.get("user_id") or p.get("id") or "")\n    if not igid:raise HTTPException(400,"Instagram did not return a professional account ID")\n    c=db.scalar(select(InstagramConnection).where(InstagramConnection.user_id==uid))\n    if not c:c=InstagramConnection(user_id=uid,access_token="",ig_user_id=igid);db.add(c)\n    c.access_token=data["access_token"];c.ig_user_id=igid;c.username=p.get("username","");c.account_type=p.get("account_type","");c.expires_in=data.get("expires_in");db.commit()\n    return RedirectResponse("/?instagram=connected")\n\n@app.get("/api/instagram/profile")\nasync def ig_profile(u:User=Depends(current_user)):\n    if not u.instagram:raise HTTPException(400,"Instagram not connected")\n    try:return await instagram.profile(u.instagram.access_token)\n    except Exception as e:raise HTTPException(400,f"Instagram profile check failed: {e}")\n\n@app.post("/api/videos/{vid}/instagram")\nasync def ig_publish(vid:int,u:User=Depends(current_user),db:Session=Depends(get_db)):\n    if not u.instagram:raise HTTPException(400,"Instagram not connected")\n    v=db.scalar(select(Video).where(Video.id==vid,Video.user_id==u.id))\n    if not v or v.status!="approved" or not v.video_path:raise HTTPException(400,"Approved MP4 required")\n    i=db.get(Idea,v.idea_id)\n    app_url=os.getenv("APP_URL","").rstrip("/")\n    if not app_url:raise HTTPException(500,"APP_URL is not configured")\n    video_url=app_url+v.video_path\n    try:\n        created=await instagram.create_reel(u.instagram.access_token,u.instagram.ig_user_id,video_url,i.caption)\n        cid=str(created.get("id") or "")\n        if not cid:raise RuntimeError("Instagram did not return a media container ID")\n        rec=InstagramPublish(user_id=u.id,video_id=v.id,container_id=cid,status="processing");db.add(rec);db.commit();db.refresh(rec)\n        import asyncio\n        last={}\n        for _ in range(20):\n            await asyncio.sleep(3)\n            last=await instagram.container_status(u.instagram.access_token,cid)\n            status=last.get("status_code")\n            if status=="FINISHED":\n                published=await instagram.publish(u.instagram.access_token,u.instagram.ig_user_id,cid)\n                rec.media_id=str(published.get("id") or "");rec.status="published";db.commit()\n                return {"status":"published","container_id":cid,"media_id":rec.media_id}\n            if status in ("ERROR","EXPIRED"):\n                rec.status=str(status).lower();db.commit();raise RuntimeError(last.get("status") or status)\n        rec.status="processing";db.commit()\n        return {"status":"processing","container_id":cid,"detail":last}\n    except HTTPException:raise\n    except Exception as e:raise HTTPException(400,f"Instagram publish failed: {e}")\n\n@app.get("/api/videos/{vid}/instagram-status")\nasync def ig_publish_status(vid:int,u:User=Depends(current_user),db:Session=Depends(get_db)):\n    rec=db.scalar(select(InstagramPublish).where(InstagramPublish.video_id==vid,InstagramPublish.user_id==u.id).order_by(InstagramPublish.id.desc()))\n    if not rec:raise HTTPException(404,"No Instagram publish attempt found")\n    if rec.status=="published":return {"status":"published","media_id":rec.media_id,"container_id":rec.container_id}\n    x=await instagram.container_status(u.instagram.access_token,rec.container_id)\n    if x.get("status_code")=="FINISHED":\n        p=await instagram.publish(u.instagram.access_token,u.instagram.ig_user_id,rec.container_id);rec.media_id=str(p.get("id") or "");rec.status="published";db.commit();return {"status":"published","media_id":rec.media_id,"container_id":rec.container_id}\n    return x\n'''
main.write_text(s)

h=html.read_text()
h=h.replace('One app for opportunity discovery, content production, TikTok export and revenue optimization.','One app for opportunity discovery, content production, Instagram/TikTok publishing and revenue optimization.')
old='<div class="card"><h2>TikTok</h2><p id="ttstate" class="muted"></p><button class="btn g" onclick="connectTikTok()">Connect TikTok</button><button class="btn" onclick="creator()">Check Creator Info</button><pre id="ttout" class="muted" style="white-space:pre-wrap"></pre></div>'
new=old+'<div class="card"><h2>Instagram</h2><p id="igstate" class="muted"></p><button class="btn g" onclick="connectInstagram()">Connect Instagram</button><button class="btn" onclick="igProfile()">Check Instagram Profile</button><pre id="igout" class="muted" style="white-space:pre-wrap"></pre><p class="muted">Requires an Instagram Professional (Business or Creator) account.</p></div>'
h=h.replace(old,new)
h=h.replace('async function creator(){try{$("ttout").textContent=JSON.stringify(await A("/api/tiktok/creator"),null,2)}catch(e){$("ttout").textContent=e.message}}','async function creator(){try{$("ttout").textContent=JSON.stringify(await A("/api/tiktok/creator"),null,2)}catch(e){$("ttout").textContent=e.message}}\nasync function connectInstagram(){try{let x=await A("/api/instagram/connect");location.href=x.url}catch(e){alert(e.message)}}\nasync function igProfile(){try{$（"igout"）.textContent=JSON.stringify(await A("/api/instagram/profile"),null,2)}catch(e){$("igout").textContent=e.message}}\nasync function igPost(id){if(!confirm("Publish this approved video as an Instagram Reel?"))return;try{let x=await A(`/api/videos/${id}/instagram`,{method:"POST"});alert(x.status==="published"?"Instagram Reel published.":"Instagram is still processing the Reel. You can retry shortly.");load()}catch(e){alert(e.message)}}')
# repair accidental full-width JS punctuation if present
h=h.replace('$（"igout"）','$('+'"igout"'+')')
h=h.replace('$("ttstate").textContent=S.tiktok_connected?"TikTok connected.":"TikTok not connected.";','$("ttstate").textContent=S.tiktok_connected?"TikTok connected.":"TikTok not connected.";$("igstate").textContent=S.instagram_connected?"Instagram connected.":(S.instagram_configured?"Instagram ready to connect.":"Instagram API setup required.");')
h=h.replace('${v.status==="approved"&&v.video_path?`<button class="btn g" onclick="tt(${v.id},\'draft\')">TikTok Draft</button><button class="btn" onclick="tt(${v.id},\'direct\')">Direct Post</button>`:""}','${v.status==="approved"&&v.video_path?`<button class="btn g" onclick="igPost(${v.id})">Post Instagram Reel</button><button class="btn" onclick="tt(${v.id},\'draft\')">TikTok Draft</button><button class="btn" onclick="tt(${v.id},\'direct\')">Direct Post</button>`:""}')
html.write_text(h)
print('Instagram integration patch applied')
