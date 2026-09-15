from pathlib import Path

# ThemeForge review mode: the TikTok app requests user.info.basic + video.upload only.
# Creator Info is a Direct Post endpoint and requires video.publish, so replace the
# review helper with TikTok's user-info endpoint for the authorized account.
p = Path('/app/app/tiktok.py')
s = p.read_text()
old = '''async def creator(token):
    async with httpx.AsyncClient(timeout=30) as c:
        r=await c.post(API+"/v2/post/publish/creator_info/query/",headers={"Authorization":f"Bearer {token}","Content-Type":"application/json; charset=UTF-8"});r.raise_for_status();return r.json()'''
new = '''async def creator(token):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(
            API + "/v2/user/info/?fields=open_id,union_id,avatar_url,display_name",
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json()'''
if old not in s:
    raise SystemExit('Expected TikTok creator helper not found; refusing to patch')
s = s.replace(old, new)
p.write_text(s)

# Rename the UI control so the review/demo accurately describes user.info.basic.
f = Path('/app/app/static/index.html')
html = f.read_text()
html = html.replace('Check Creator Info', 'Check TikTok Profile')
f.write_text(html)
print('TikTok review profile check patched for user.info.basic')
