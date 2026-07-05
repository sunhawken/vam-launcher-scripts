"""
Fix Coffy.50_animated_sex_loops.3.var -> .4.var
Strip all Play Anim N from NEXT and PREV buttons (correct pattern: navigate only).
PLAY button already has Play Current Clip - leave it.
"""
import zipfile, json, re, os, shutil, subprocess, tempfile, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SEVENZIP   = r"C:\Program Files\7-Zip\7z.exe"
BACKUP_DIR = r"T:\New folder\backup"
COFFY_DIR  = r"T:\New folder\AddonPackages\cleaned"

VT_PLUGIN  = "plugin#0_VamTimeline.AtomPlugin"

VAR_IN  = os.path.join(COFFY_DIR, "Coffy.50_animated_sex_loops.3.var")
VAR_OUT = os.path.join(COFFY_DIR, "Coffy.50_animated_sex_loops.4.var")

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)

def repack(files, var_out):
    tmpdir = tempfile.mkdtemp()
    try:
        for rel, data in files.items():
            if rel.endswith('/'): continue
            dst = os.path.join(tmpdir, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f: f.write(data)
        tmp = os.path.join(tempfile.gettempdir(), '_coffy_fix.zip')
        if os.path.exists(tmp): os.remove(tmp)
        r = subprocess.run([SEVENZIP,'a','-tzip','-mx=1',tmp,
                            os.path.join(tmpdir,'*')], capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError('7z: ' + r.stdout[-500:])
        shutil.copy2(tmp, var_out); os.remove(tmp)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

def is_play_anim(action):
    """True if this action is a VamTimeline Play Anim N (not Play Current Clip)."""
    return (action.get('receiver') == VT_PLUGIN and
            'Play' in action.get('receiverTargetName','') and
            action.get('receiverTargetName') != 'Play Current Clip')

# Backup
bk = os.path.join(BACKUP_DIR, os.path.basename(VAR_IN))
if not os.path.exists(bk):
    shutil.copy2(VAR_IN, bk)
    print(f"Backed up to {bk}")
else:
    print(f"Backup already exists: {bk}")

with zipfile.ZipFile(VAR_IN, 'r') as z:
    files = {n: z.read(n) for n in z.namelist()}

scene_file = next(n for n in files if n.endswith('.json') and 'scene' in n.lower())
print(f"Scene: {scene_file}")

raw   = fix_json(files[scene_file].decode('utf-8-sig', errors='replace'))
scene = json.loads(raw)

cc = next(a for a in scene['atoms'] if a.get('id') == 'CoreControl')
dk = next(s for s in cc['storables'] if 'DockedUI' in s.get('id',''))

cnt = int(dk.get('Count', dk.get('counts','4')))
for i in range(cnt):
    bn = dk.get(f'ButtonWidget{i}',{}).get('name','')
    if bn not in ('NEXT','PREV'): continue
    ak = bn + str(i)

    entry = dk.get(ak, {})
    start_before = entry.get('startActions', [])
    start_after  = [a for a in start_before if not is_play_anim(a)]

    removed = len(start_before) - len(start_after)
    print(f"  {bn}: removed {removed} Play Anim N actions, kept {len(start_after)} actions:")
    for a in start_after:
        print(f"    {a.get('receiverTargetName','')} on {a.get('receiverAtom','')}")

    entry['startActions'] = start_after
    dk[ak] = entry

    # Mirror in Actions tab
    if 'Actions' in dk and ak in dk['Actions']:
        inner = dk['Actions'][ak]
        inner['startActions'] = [a for a in inner.get('startActions',[]) if not is_play_anim(a)]
        dk['Actions'][ak] = inner

# Update LoadPresetPath to new pkg ref
old_ref = "Coffy.50_animated_sex_loops.3"
new_ref = "Coffy.50_animated_sex_loops.4"
if 'LoadPresetPath' in dk:
    dk['LoadPresetPath'] = dk['LoadPresetPath'].replace(old_ref, new_ref)
    print(f"\n  LoadPresetPath updated to .4")

# Update preset files with new ref
for preset_path in list(files.keys()):
    if 'DockedUIPreset' in preset_path:
        files[preset_path] = files[preset_path].replace(
            old_ref.encode(), new_ref.encode())

files[scene_file] = json.dumps(scene, indent=3, ensure_ascii=False).encode('utf-8')

# meta.json: bump nothing, just keep existing
repack(files, VAR_OUT)

# Verify
with zipfile.ZipFile(VAR_OUT) as z:
    raw2 = fix_json(z.read(scene_file).decode('utf-8-sig','replace'))
s2 = json.loads(raw2)
cc2 = next(a for a in s2['atoms'] if a.get('id') == 'CoreControl')
dk2 = next(s for s in cc2['storables'] if 'DockedUI' in s.get('id',''))
cnt2 = int(dk2.get('Count', dk2.get('counts','0')))
print(f"\nVerify output:")
for i in range(cnt2):
    bn = dk2.get(f'ButtonWidget{i}',{}).get('name','')
    ak = bn + str(i)
    starts = dk2.get(ak,{}).get('startActions',[])
    play_anim_found = [a.get('receiverTargetName') for a in starts if is_play_anim(a)]
    nav_found = [a.get('receiverTargetName') for a in starts if not is_play_anim(a)]
    print(f"  {bn}: nav={nav_found}  play_anim_leftover={play_anim_found}")

sz = round(os.path.getsize(VAR_OUT)/1024/1024, 1)
print(f"\nOK  {os.path.basename(VAR_OUT)}  [{sz}MB]")
print("Deleting .3.var ...")
os.remove(VAR_IN)
print("Done.")
