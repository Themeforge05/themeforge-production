from pathlib import Path

p = Path('/app/app/static/index.html')
s = p.read_text()
original = s

s = s.replace('>Open MP4</a>', '>▶ Preview Video</a>')
s = s.replace('>Video</a>', '>▶ Preview Video</a>')
s = s.replace('>MP4</a>', '>▶ Preview Video</a>')

old_review = 'async function review(id,a){await A(`/api/videos/${id}/${a}`,{method:"POST"});load()}'
new_review = '''async function review(id,a){let v=(S.videos||[]).find(x=>x.id===id);if(a==="approve"&&(!v||!v.video_path)){alert("This video cannot be approved because there is no playable MP4. Produce a new video first.");return}await A(`/api/videos/${id}/${a}`,{method:"POST"});load()}'''
if old_review not in s:
    raise SystemExit('Expected review function not found; refusing to patch')
s = s.replace(old_review, new_review)

old_actions = '''${v.status==="pending_approval"?`<button class="btn" onclick="review(${v.id},'reject')">Reject</button><button class="btn g" onclick="review(${v.id},'approve')">Approve</button>`:""}'''
new_actions = '''${v.status==="pending_approval"&&v.video_path?`<button class="btn" onclick="review(${v.id},'reject')">Reject</button><button class="btn g" onclick="review(${v.id},'approve')">Approve</button>`:""}${!v.video_path&&v.status!=="rendering"&&v.status!=="queued"?`<span class="muted">No preview available because rendering failed. Produce a new video after the renderer update.</span>`:""}'''
if old_actions in s:
    s = s.replace(old_actions, new_actions)

p.write_text(s)
print('ThemeForge preview and approval UI patched; changed=', s != original)
