from pathlib import Path

p = Path('/app/app/static/index.html')
s = p.read_text()

# Patch the production card renderer at build time without depending on one exact minified layout.
# A valid mp4_path gets an inline HTML5 player. Failed/no-MP4 items cannot be approved.
needle = '${v.notes||""}'
if needle not in s:
    # tolerate alternate field rendering used by the bundled frontend
    needle = '${v.notes}'
if needle not in s:
    raise SystemExit('Video notes template not found; refusing blind UI patch')

preview = '''${v.mp4_path?`<div style="margin:12px 0"><video controls preload="metadata" playsinline style="width:min(100%,360px);max-height:640px;border-radius:14px;background:#000" src="/generated/${v.mp4_path.split('/').pop()}"></video><div style="margin-top:6px;font-weight:700">▶ Preview Video — watch before approving</div></div>`:`<div style="margin:12px 0;padding:10px 12px;border:1px solid #7f1d1d;border-radius:10px"><b>Render Failed</b> — no playable MP4 was created. Generate a new video after the renderer is fixed.</div>`}${v.notes||""}'''
s = s.replace(needle, preview, 1)

# Gate Approve at the click handler as a second line of defense. This keeps failed videos
# from being approved even if an old card/button remains visible in cached markup.
old = 'async function act(id,a){await A(`/api/videos/${id}/${a}`,{method:"POST"});await load()}'
new = '''async function act(id,a){let v=(S.videos||[]).find(x=>x.id===id);if(a==="approve"&&(!v||!v.mp4_path)){alert("This video cannot be approved because rendering failed and there is no playable MP4. Generate a new video first.");return}await A(`/api/videos/${id}/${a}`,{method:"POST"});await load()}'''
if old in s:
    s = s.replace(old,new)

p.write_text(s)
print('ThemeForge production UI patched: inline preview + approval gating')
