from pathlib import Path

p = Path('/app/app/static/index.html')
s = p.read_text()
s2 = s.replace('>Video</a>', '>Preview Video</a>').replace('>Open MP4</a>', '>Preview Video</a>').replace('>MP4</a>', '>Preview Video</a>')
if s2 == s:
    raise SystemExit('No known video preview anchor found; refusing to patch blindly')
p.write_text(s2)
print('ThemeForge production preview label patched')
