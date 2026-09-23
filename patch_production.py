from pathlib import Path

p = Path('/app/app/main.py')
s = p.read_text()
original = s

old_complete = '''        v.render_message=msg;v.status="pending_approval";i.status="produced";db.commit()'''
new_complete = '''        v.render_message=msg
        v.status="pending_approval" if v.video_path else "failed"
        i.status="produced" if v.video_path else "render_failed"
        db.commit()'''
if old_complete not in s:
    raise SystemExit('Expected production completion line not found; refusing to patch')
s = s.replace(old_complete, new_complete)

old_review = '''    if action not in ("approve","reject"):raise HTTPException(400,"Invalid action")
    v.status="approved" if action=="approve" else "rejected";db.commit();return {"status":v.status}'''
new_review = '''    if action not in ("approve","reject"):raise HTTPException(400,"Invalid action")
    if action=="approve" and not v.video_path:
        raise HTTPException(400,"Cannot approve a video without a playable MP4")
    v.status="approved" if action=="approve" else "rejected";db.commit();return {"status":v.status}'''
if old_review not in s:
    raise SystemExit('Expected review handler not found; refusing to patch')
s = s.replace(old_review, new_review)

p.write_text(s)
print('ThemeForge production states and approval guard patched; changed=', s != original)
