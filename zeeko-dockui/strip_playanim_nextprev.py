"""
Strip all Play Anim N from NEXT and PREV DockedUI buttons across all Zeeko .var files.
POSE_STUDIO_P1/P2 are excluded (they have no Play Anim N, different issue).
Saves as next version, deletes old file.
"""
import zipfile, json, re, os, shutil, subprocess, tempfile, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SEVENZIP   = r"C:\Program Files\7-Zip\7z.exe"
BACKUP_DIR = r"T:\New folder\backup"
ZEEKO      = r"T:\New folder\AddonPackages\cleaned\Zeeko"

VT_PLUGIN = "plugin#0_VamTimeline.AtomPlugin"
SKIP = {"Zeeko.POSE_STUDIO_P1", "Zeeko.POSE_STUDIO_P2"}

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)

def pkg_name(fname):
    base = fname.replace('.DISABLED','').replace('.var','')
    return base.rsplit('.', 1)[0]

def pkg_ver(fname):
    base = fname.replace('.DISABLED','').replace('.var','')
    try: return int(base.rsplit('.', 1)[1])
    except: return 0

def is_play_anim(action):
    return (action.get('receiver') == VT_PLUGIN and
            'Play' in action.get('receiverTargetName','') and
            action.get('receiverTargetName') != 'Play Current Clip')

def repack(files, var_out):
    tmpdir = tempfile.mkdtemp()
    try:
        for rel, data in files.items():
            if rel.endswith('/'): continue
            dst = os.path.join(tmpdir, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f: f.write(data)
        tmp = os.path.join(tempfile.gettempdir(), '_strip_playanim.zip')
        if os.path.exists(tmp): os.remove(tmp)
        r = subprocess.run([SEVENZIP,'a','-tzip','-mx=1',tmp,
                            os.path.join(tmpdir,'*')], capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError('7z: ' + r.stdout[-500:])
        shutil.copy2(tmp, var_out); os.remove(tmp)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# Collect all .var files (skip POSE_STUDIO, skip par2)
targets = []
for f in sorted(os.listdir(ZEEKO)):
    if not f.endswith('.var'): continue
    if '.par2' in f: continue
    pkg = pkg_name(f)
    if pkg in SKIP: continue
    targets.append(os.path.join(ZEEKO, f))

print(f"Processing {len(targets)} files\n")
ok, skip_clean, fail = [], [], []

for var_in in targets:
    fname = os.path.basename(var_in)
    try:
        ver = pkg_ver(fname)
        pkg = pkg_name(fname)
        var_out = os.path.join(ZEEKO, f"{pkg}.{ver+1}.var")

        # Backup
        bk = os.path.join(BACKUP_DIR, fname)
        if not os.path.exists(bk):
            shutil.copy2(var_in, bk)

        with zipfile.ZipFile(var_in,'r') as z:
            files = {n: z.read(n) for n in z.namelist()}

        scene_file = next(n for n in files if n.endswith('.json') and 'scene' in n.lower())
        raw   = fix_json(files[scene_file].decode('utf-8-sig', errors='replace'))
        scene = json.loads(raw)

        cc = next((a for a in scene['atoms'] if a.get('id') == 'CoreControl'), None)
        if not cc: raise RuntimeError('no CoreControl')
        dk = next((s for s in cc['storables'] if 'DockedUI' in s.get('id','')), None)
        if not dk: raise RuntimeError('no DockedUI')

        cnt = int(dk.get('Count', dk.get('counts','4')))
        total_removed = 0

        for i in range(cnt):
            bn = dk.get(f'ButtonWidget{i}',{}).get('name','')
            if bn not in ('NEXT','PREV'): continue
            ak = bn + str(i)

            entry = dk.get(ak, {})
            before = entry.get('startActions', [])
            after  = [a for a in before if not is_play_anim(a)]
            removed = len(before) - len(after)
            total_removed += removed
            entry['startActions'] = after
            dk[ak] = entry

            if 'Actions' in dk and ak in dk['Actions']:
                inner = dk['Actions'][ak]
                inner['startActions'] = [a for a in inner.get('startActions',[]) if not is_play_anim(a)]
                dk['Actions'][ak] = inner

        if total_removed == 0:
            skip_clean.append(fname)
            print(f"SKIP {fname}  (no Play Anim N found on NEXT/PREV)")
            continue

        # Update LoadPresetPath
        old_ref = f"{pkg}.{ver}"
        new_ref = f"{pkg}.{ver+1}"
        if 'LoadPresetPath' in dk:
            dk['LoadPresetPath'] = dk['LoadPresetPath'].replace(old_ref, new_ref)

        # Update preset file refs
        for ppath in list(files.keys()):
            if 'DockedUIPreset' in ppath:
                files[ppath] = files[ppath].replace(old_ref.encode(), new_ref.encode())

        files[scene_file] = json.dumps(scene, indent=3, ensure_ascii=False).encode('utf-8')

        repack(files, var_out)

        # Verify: no Play Anim N left on NEXT/PREV
        with zipfile.ZipFile(var_out) as z:
            raw2 = fix_json(z.read(scene_file).decode('utf-8-sig','replace'))
        s2 = json.loads(raw2)
        cc2 = next(a for a in s2['atoms'] if a.get('id') == 'CoreControl')
        dk2 = next(s for s in cc2['storables'] if 'DockedUI' in s.get('id',''))
        cnt2 = int(dk2.get('Count', dk2.get('counts','0')))
        for i in range(cnt2):
            bn = dk2.get(f'ButtonWidget{i}',{}).get('name','')
            if bn not in ('NEXT','PREV'): continue
            ak = bn + str(i)
            leftover = [a for a in dk2.get(ak,{}).get('startActions',[]) if is_play_anim(a)]
            if leftover:
                raise RuntimeError(f"{bn} still has Play Anim N: {[a.get('receiverTargetName') for a in leftover]}")

        sz = round(os.path.getsize(var_out)/1024/1024, 1)
        print(f"OK  {fname} -> {os.path.basename(var_out)}  [{sz}MB]  stripped={total_removed}")
        ok.append(fname)
        os.remove(var_in)

    except Exception as e:
        import traceback
        print(f"FAIL {fname}: {e}")
        traceback.print_exc()
        fail.append((fname, str(e)))

print(f"\n=== Done: {len(ok)} OK, {len(skip_clean)} already clean, {len(fail)} FAIL ===")
for f, e in fail:
    print(f"  FAIL: {f}: {e}")
