"""
For every Zeeko .var (skip POSE_STUDIO):
  1. Identify leader atoms = get Play Anim N from UIButton triggers
  2. Identify follower atoms = VT atoms not in leaders
  3. Strip followers from PLAY (Play Current Clip), NEXT (Next Animation), PREV (Previous Animation)
  4. Leaders stay on all three buttons
  5. STOP untouched (Stop And Reset on all VT atoms is correct)
  6. Save as next version, delete old
"""
import zipfile, json, re, os, shutil, subprocess, tempfile, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SEVENZIP   = r"C:\Program Files\7-Zip\7z.exe"
BACKUP_DIR = r"T:\New folder\backup"
ZEEKO      = r"T:\New folder\AddonPackages\cleaned\Zeeko"
VT         = "plugin#0_VamTimeline.AtomPlugin"
SKIP       = {"Zeeko.POSE_STUDIO_P1", "Zeeko.POSE_STUDIO_P2"}

NAV_TARGETS = {'Next Animation', 'Previous Animation', 'Play Current Clip'}

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)
def pkg_name(f): return f.replace('.DISABLED','').replace('.var','').rsplit('.',1)[0]
def pkg_ver(f):
    base = f.replace('.DISABLED','').replace('.var','')
    try: return int(base.rsplit('.',1)[1])
    except: return 0

def repack(files, var_out):
    tmpdir = tempfile.mkdtemp()
    try:
        for rel, data in files.items():
            if rel.endswith('/'): continue
            dst = os.path.join(tmpdir, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f: f.write(data)
        tmp = os.path.join(tempfile.gettempdir(), '_follower_fix.zip')
        if os.path.exists(tmp): os.remove(tmp)
        r = subprocess.run([SEVENZIP,'a','-tzip','-mx=1',tmp,
                            os.path.join(tmpdir,'*')], capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError('7z: ' + r.stdout[-500:])
        shutil.copy2(tmp, var_out); os.remove(tmp)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

targets = []
for f in sorted(os.listdir(ZEEKO)):
    if not f.endswith('.var') or '.par2' in f: continue
    if pkg_name(f) in SKIP: continue
    targets.append(os.path.join(ZEEKO, f))

print(f"Processing {len(targets)} files\n")
ok, fail = [], []

for var_in in targets:
    fname = os.path.basename(var_in)
    try:
        ver = pkg_ver(fname)
        pkg = pkg_name(fname)
        var_out = os.path.join(ZEEKO, f"{pkg}.{ver+1}.var")

        bk = os.path.join(BACKUP_DIR, fname)
        if not os.path.exists(bk): shutil.copy2(var_in, bk)

        with zipfile.ZipFile(var_in,'r') as z:
            files = {n: z.read(n) for n in z.namelist()}

        sf = next(n for n in files if n.endswith('.json') and 'scene' in n.lower())
        scene = json.loads(fix_json(files[sf].decode('utf-8-sig','replace')))

        # Identify VT atoms
        vt_atoms = set()
        for atom in scene.get('atoms',[]):
            for s in atom.get('storables',[]):
                if s.get('id') == VT:
                    vt_atoms.add(atom['id'])

        # Leaders = atoms that receive Play Anim N from UIButtons
        leaders = set()
        for atom in scene.get('atoms',[]):
            if atom.get('type') != 'UIButton': continue
            for s in atom.get('storables',[]):
                for a in s.get('trigger',{}).get('startActions',[]):
                    if (a.get('receiver') == VT and
                            'Play' in a.get('receiverTargetName','') and
                            a.get('receiverTargetName') != 'Play Current Clip'):
                        leaders.add(a.get('receiverAtom',''))

        followers = vt_atoms - leaders
        if not followers:
            print(f"SKIP {fname}  (no followers detected, leaders={sorted(leaders)})")
            ok.append(fname + ' [no-followers]')
            continue

        cc = next(a for a in scene['atoms'] if a.get('id') == 'CoreControl')
        dk = next(s for s in cc['storables'] if 'DockedUI' in s.get('id',''))
        cnt = int(dk.get('Count', dk.get('counts','4')))

        total_removed = 0
        for i in range(cnt):
            bn = dk.get(f'ButtonWidget{i}',{}).get('name','')
            if bn not in ('PLAY','NEXT','PREV'): continue
            ak = bn + str(i)

            entry = dk.get(ak, {})
            before = entry.get('startActions', [])

            # Remove actions where atom is a follower AND target is a nav/play target
            after = [a for a in before
                     if not (a.get('receiverAtom','') in followers and
                             a.get('receiverTargetName','') in NAV_TARGETS)]
            removed = len(before) - len(after)
            total_removed += removed
            entry['startActions'] = after
            dk[ak] = entry

            if 'Actions' in dk and ak in dk['Actions']:
                inner = dk['Actions'][ak]
                inner['startActions'] = [a for a in inner.get('startActions',[])
                                          if not (a.get('receiverAtom','') in followers and
                                                  a.get('receiverTargetName','') in NAV_TARGETS)]
                dk['Actions'][ak] = inner

        if total_removed == 0:
            print(f"SKIP {fname}  (nothing to remove, followers={sorted(followers)})")
            ok.append(fname + ' [already-clean]')
            continue

        # Update LoadPresetPath and preset file refs
        old_ref = f"{pkg}.{ver}"
        new_ref = f"{pkg}.{ver+1}"
        if 'LoadPresetPath' in dk:
            dk['LoadPresetPath'] = dk['LoadPresetPath'].replace(old_ref, new_ref)
        for ppath in list(files.keys()):
            if 'DockedUIPreset' in ppath:
                files[ppath] = files[ppath].replace(old_ref.encode(), new_ref.encode())

        files[sf] = json.dumps(scene, indent=3, ensure_ascii=False).encode('utf-8')
        repack(files, var_out)

        # Verify: no follower atoms left on PLAY/NEXT/PREV for nav targets
        with zipfile.ZipFile(var_out) as z:
            raw2 = fix_json(z.read(sf).decode('utf-8-sig','replace'))
        s2 = json.loads(raw2)
        cc2 = next(a for a in s2['atoms'] if a.get('id') == 'CoreControl')
        dk2 = next(s for s in cc2['storables'] if 'DockedUI' in s.get('id',''))
        cnt2 = int(dk2.get('Count', dk2.get('counts','0')))
        for i in range(cnt2):
            bn = dk2.get(f'ButtonWidget{i}',{}).get('name','')
            if bn not in ('PLAY','NEXT','PREV'): continue
            ak = bn + str(i)
            leftover = [a for a in dk2.get(ak,{}).get('startActions',[])
                        if a.get('receiverAtom','') in followers and
                           a.get('receiverTargetName','') in NAV_TARGETS]
            if leftover:
                raise RuntimeError(f"{bn} still has follower actions: {leftover}")

        sz = round(os.path.getsize(var_out)/1024/1024, 1)
        print(f"OK  {fname} -> {os.path.basename(var_out)}  [{sz}MB]"
              f"  leaders={sorted(leaders)}  followers={sorted(followers)}  stripped={total_removed}")
        ok.append(fname)
        os.remove(var_in)

    except Exception as e:
        import traceback
        print(f"FAIL {fname}: {e}")
        traceback.print_exc()
        fail.append((fname, str(e)))

print(f"\n=== Done: {len(ok)} OK, {len(fail)} FAIL ===")
for f, e in fail:
    print(f"  FAIL: {f}: {e}")
