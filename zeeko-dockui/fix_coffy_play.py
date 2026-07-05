"""
Fix Coffy.50_animated_sex_loops.4.var -> .5.var
PLAY button: remove Play Current Clip from female, keep only male.
"""
import zipfile, json, re, os, shutil, subprocess, tempfile, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SEVENZIP   = r"C:\Program Files\7-Zip\7z.exe"
BACKUP_DIR = r"T:\New folder\backup"
COFFY_DIR  = r"T:\New folder\AddonPackages\cleaned"

VAR_IN  = os.path.join(COFFY_DIR, "Coffy.50_animated_sex_loops.4.var")
VAR_OUT = os.path.join(COFFY_DIR, "Coffy.50_animated_sex_loops.5.var")

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)

def repack(files, var_out):
    tmpdir = tempfile.mkdtemp()
    try:
        for rel, data in files.items():
            if rel.endswith('/'): continue
            dst = os.path.join(tmpdir, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f: f.write(data)
        tmp = os.path.join(tempfile.gettempdir(), '_coffy_play_fix.zip')
        if os.path.exists(tmp): os.remove(tmp)
        r = subprocess.run([SEVENZIP,'a','-tzip','-mx=1',tmp,
                            os.path.join(tmpdir,'*')], capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError('7z: ' + r.stdout[-500:])
        shutil.copy2(tmp, var_out); os.remove(tmp)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

bk = os.path.join(BACKUP_DIR, os.path.basename(VAR_IN))
if not os.path.exists(bk): shutil.copy2(VAR_IN, bk)

with zipfile.ZipFile(VAR_IN,'r') as z:
    files = {n: z.read(n) for n in z.namelist()}

scene_file = next(n for n in files if n.endswith('.json') and 'scene' in n.lower())
raw   = fix_json(files[scene_file].decode('utf-8-sig', errors='replace'))
scene = json.loads(raw)

cc = next(a for a in scene['atoms'] if a.get('id') == 'CoreControl')
dk = next(s for s in cc['storables'] if 'DockedUI' in s.get('id',''))

cnt = int(dk.get('Count', dk.get('counts','4')))
for i in range(cnt):
    bn = dk.get(f'ButtonWidget{i}',{}).get('name','')
    if bn != 'PLAY': continue
    ak = bn + str(i)

    entry = dk.get(ak, {})
    before = entry.get('startActions', [])
    print(f"PLAY before: {[(a.get('receiverAtom',''), a.get('receiverTargetName','')) for a in before]}")

    # Keep only non-female Play Current Clip entries
    after = [a for a in before
             if not (a.get('receiverTargetName') == 'Play Current Clip'
                     and a.get('receiverAtom') == 'female')]
    print(f"PLAY after:  {[(a.get('receiverAtom',''), a.get('receiverTargetName','')) for a in after]}")

    entry['startActions'] = after
    dk[ak] = entry

    if 'Actions' in dk and ak in dk['Actions']:
        inner = dk['Actions'][ak]
        inner['startActions'] = [a for a in inner.get('startActions',[])
                                  if not (a.get('receiverTargetName') == 'Play Current Clip'
                                          and a.get('receiverAtom') == 'female')]
        dk['Actions'][ak] = inner

# Update LoadPresetPath
old_ref = "Coffy.50_animated_sex_loops.4"
new_ref = "Coffy.50_animated_sex_loops.5"
if 'LoadPresetPath' in dk:
    dk['LoadPresetPath'] = dk['LoadPresetPath'].replace(old_ref, new_ref)
for ppath in list(files.keys()):
    if 'DockedUIPreset' in ppath:
        files[ppath] = files[ppath].replace(old_ref.encode(), new_ref.encode())

files[scene_file] = json.dumps(scene, indent=3, ensure_ascii=False).encode('utf-8')
repack(files, VAR_OUT)

# Verify
with zipfile.ZipFile(VAR_OUT) as z:
    raw2 = fix_json(z.read(scene_file).decode('utf-8-sig','replace'))
s2 = json.loads(raw2)
cc2 = next(a for a in s2['atoms'] if a.get('id') == 'CoreControl')
dk2 = next(s for s in cc2['storables'] if 'DockedUI' in s.get('id',''))
cnt2 = int(dk2.get('Count', dk2.get('counts','0')))
for i in range(cnt2):
    bn = dk2.get(f'ButtonWidget{i}',{}).get('name','')
    ak = bn + str(i)
    starts = dk2.get(ak,{}).get('startActions',[])
    print(f"  {bn}: {[(a.get('receiverAtom',''), a.get('receiverTargetName','')) for a in starts]}")

sz = round(os.path.getsize(VAR_OUT)/1024/1024, 1)
print(f"\nOK  {os.path.basename(VAR_OUT)}  [{sz}MB]")
os.remove(VAR_IN)
print("Done.")
