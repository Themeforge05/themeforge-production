from pathlib import Path

p = Path('/app/app/static/index.html')
s = p.read_text()

# Do not fail the production build when an older bundled frontend lacks the exact notes template.
# Prefer enhancing existing MP4 links, which is compatible with the current production bundle.
original = s
s = s.replace('>Open MP4</a>', '>▶ Preview Video</a>')
s = s.replace('>Video</a>', '>▶ Preview Video</a>')
s = s.replace('>MP4</a>', '>▶ Preview Video</a>')

# Gate approval when the known action handler is present.
old = 'async function act(id,a){await A(`/api/videos/${id}/${a}`,{method:"POST"});await load()}'
new = '''async function act(id,a){let v=(S.videos||[]).find(x=>x.id===id);if(a==="approve"&&(!v||!v.mp4_path)){alert("This video cannot be approved because there is no playable MP4. Generate a new video first.");return}await A(`/api/videos/${id}/${a}`,{method:"POST"});await load()}'''
if old in s:
    s = s.replace(old,new)

p.write_text(s)
print('ThemeForge preview patch applied; changed=', s != original)
