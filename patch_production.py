from pathlib import Path

p = Path('/app/app/main.py')
s = p.read_text()
original = s

# Production runs in a background task. Ensure its completion path only marks a video
# pending approval when render() actually returned a valid MP4 path.
# Patch common assignment forms used by the bundled app without changing auth/routes.
repls = [
    ('v.poster_path,v.mp4_path,v.notes=await render(v.video_id,idea)\n        v.status="pending_approval"',
     'v.poster_path,v.mp4_path,v.notes=await render(v.video_id,idea)\n        v.status="pending_approval" if v.mp4_path else "failed"'),
    ('video.poster_path,video.mp4_path,video.notes=await render(video.video_id,idea)\n        video.status="pending_approval"',
     'video.poster_path,video.mp4_path,video.notes=await render(video.video_id,idea)\n        video.status="pending_approval" if video.mp4_path else "failed"'),
    ('v.poster_path, v.mp4_path, v.notes = await render(v.video_id, idea)\n        v.status = "pending_approval"',
     'v.poster_path, v.mp4_path, v.notes = await render(v.video_id, idea)\n        v.status = "pending_approval" if v.mp4_path else "failed"'),
]
for old,new in repls:
    s=s.replace(old,new)

# Server-side approval guard: UI is not the security boundary.
for needle in [
    'if action not in ["approve","reject"]:',
    "if action not in ['approve','reject']:",
]:
    if needle in s and 'Cannot approve a video without a valid MP4' not in s:
        # Insert later only if exact route source exposes a usable video variable; avoid blind mutation.
        pass

p.write_text(s)
print('ThemeForge production state patch applied; changed=', s != original)
