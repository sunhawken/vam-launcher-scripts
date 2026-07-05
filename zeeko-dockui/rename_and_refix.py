"""
1. Rename all current .var files -> .DISABLED (Zeeko non-POSE_STUDIO + Coffy)
2. Re-apply nextprev autoplay fix (Next/Prev Animation + Play Current Clip on leader)
3. Verify NEXT/PREV contain exactly: navigate + Play Current Clip on leader
"""
import zipfile, json, re, os, shutil, subprocess, tempfile, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SEVENZIP   = r"C:\Program Files\7-Zip\7z.exe"
BACKUP_DIR = r"T:\New folder\backup"
ZEEKO      = r"T:\New folder\AddonPackages\cleaned\Zeeko"
COFFY_DIR  = r"T:\New folder\AddonPackages\cleaned"
VT         = "plugin#0_VamTimeline.AtomPlugin"
SKIP       = {"Zeeko.POSE_STUDIO_P1", "Zeeko.POSE_STUDIO_P2"}

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)
def pkg_name(f): return f.replace('.DISABLED','').replace('.var','').rsplit('.',1)[0]
def pkg_ver(f):
    base = f.replace('.DISABLED','').replace('.var','')
    try: return int(base.rsplit('.',1)[1])
    except: return 0

def make_action(name, atom, target):
    return {"name": name, "receiverAtom": atom, "receiver": VT, "receiverTargetName": target}

def repack(files, var_out):
    tmpdir = tempfile.mkdtemp()
    try:
        for rel, data in files.items():
            if rel.endswith('/'): continue
            dst = os.path.join(tmpdir, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f: f.write(data)
        tmp = os.path.join(tempfile.gettempdir(), '_refix.zip')
        if os.path.exists(tmp): os.remove(tmp)
        r = subprocess.run([SEVENZIP,'a','-tzip','-mx=1',tmp,
                            os.path.join(tmpdir,'*')], capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError('7z: ' + r.stdout[-500:])
        shutil.copy2(tmp, var_out); os.remove(tmp)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# ── Step 1: Collect .var files and rename to .DISABLED ───────────────────────
to_process = []  # (disabled_path, out_dir)

for f in sorted(os.listdir(ZEEKO)):
    if not f.endswith('.var') or '.par2' in f: continue
    if pkg_name(f) in SKIP: continue
    src = os.path.join(ZEEKO, f)
    dst = src.replace('.var', '.DISABLED')
    os.rename(src, dst)
    to_process.append((dst, ZEEKO))
    print(f"Renamed: {f} -> {os.path.basename(dst)}")

for f in sorted(os.listdir(COFFY_DIR)):
    if 'Coffy' not in f or not f.endswith('.var') or '.par2' in f: continue
    src = os.path.join(COFFY_DIR, f)
    dst = src.replace('.var', '.DISABLED')
    os.rename(src, dst)
    to_process.append((dst, COFFY_DIR))
    print(f"Renamed: {f} -> {os.path.basename(dst)}")

print(f"\nRenamed {len(to_process)} files. Now applying fix...\n")

# ── Step 2: Apply fix and verify ─────────────────────────────────────────────
ok, fail = [], []

for var_in, out_dir in to_process:
    fname = os.path.basename(var_in)
    try:
        ver = pkg_ver(fname)
        pkg = pkg_name(fname)
        var_out = os.path.join(out_dir, f"{pkg}.{ver+1}.var")

        bk = os.path.join(BACKUP_DIR, fname)
        if not os.path.exists(bk): shutil.copy2(var_in, bk)

        with zipfile.ZipFile(var_in,'r') as z:
            files = {n: z.read(n) for n in z.namelist()}

        sf = next(n for n in files if n.endswith('.json') and 'scene' in n.lower())
        scene = json.loads(fix_json(files[sf].decode('utf-8-sig','replace')))

        # Identify leaders from UIButton Play Anim N triggers
        leaders = set()
        for atom in scene.get('atoms',[]):
            if atom.get('type') != 'UIButton': continue
            for s in atom.get('storables',[]):
                for a in s.get('trigger',{}).get('startActions',[]):
                    if (a.get('receiver') == VT and
                            'Play' in a.get('receiverTargetName','') and
                            a.get('receiverTargetName') != 'Play Current Clip'):
                        leaders.add(a.get('receiverAtom',''))

        if not leaders:
            raise RuntimeError('no leaders found')

        cc = next(a for a in scene['atoms'] if a.get('id') == 'CoreControl')
        dk = next(s for s in cc['storables'] if 'DockedUI' in s.get('id',''))
        cnt = int(dk.get('Count', dk.get('counts','4')))

        for i in range(cnt):
            bn = dk.get(f'ButtonWidget{i}',{}).get('name','')
            if bn not in ('NEXT','PREV'): continue
            ak = bn + str(i)

            entry = dk.get(ak, {})
            start = entry.get('startActions', [])

            # Remove existing Play Current Clip on leaders (idempotent)
            start = [a for a in start if not
                     (a.get('receiverAtom','') in leaders and
                      a.get('receiverTargetName') == 'Play Current Clip')]

            # Append Play Current Clip for each leader
            for l in sorted(leaders):
                start.append(make_action(f"Play_{l}", l, "Play Current Clip"))

            entry['startActions'] = start
            dk[ak] = entry

            if 'Actions' in dk and ak in dk['Actions']:
                inner = dk['Actions'][ak]
                inner_start = [a for a in inner.get('startActions',[]) if not
                               (a.get('receiverAtom','') in leaders and
                                a.get('receiverTargetName') == 'Play Current Clip')]
                for l in sorted(leaders):
                    inner_start.append(make_action(f"Play_{l}", l, "Play Current Clip"))
                inner['startActions'] = inner_start
                dk['Actions'][ak] = inner

        old_ref = f"{pkg}.{ver}"
        new_ref = f"{pkg}.{ver+1}"
        if 'LoadPresetPath' in dk:
            dk['LoadPresetPath'] = dk['LoadPresetPath'].replace(old_ref, new_ref)
        for ppath in list(files.keys()):
            if 'DockedUIPreset' in ppath:
                files[ppath] = files[ppath].replace(old_ref.encode(), new_ref.encode())

        files[sf] = json.dumps(scene, indent=3, ensure_ascii=False).encode('utf-8')
        repack(files, var_out)

        # ── Verify ───────────────────────────────────────────────────────────
        with zipfile.ZipFile(var_out) as z:
            raw2 = fix_json(z.read(sf).decode('utf-8-sig','replace'))
        s2 = json.loads(raw2)
        cc2 = next(a for a in s2['atoms'] if a.get('id') == 'CoreControl')
        dk2 = next(s for s in cc2['storables'] if 'DockedUI' in s.get('id',''))
        cnt2 = int(dk2.get('Count', dk2.get('counts','0')))

        errors = []
        btn_summary = {}
        for i in range(cnt2):
            bn = dk2.get(f'ButtonWidget{i}',{}).get('name','')
            if bn not in ('NEXT','PREV'): continue
            ak = bn + str(i)
            starts = dk2.get(ak,{}).get('startActions',[])

            nav_tgt = 'Next Animation' if bn == 'NEXT' else 'Previous Animation'
            nav_actions   = [a for a in starts if a.get('receiverTargetName') == nav_tgt]
            play_actions  = [a for a in starts if a.get('receiverTargetName') == 'Play Current Clip']
            stray_actions = [a for a in starts if a.get('receiverTargetName') not in (nav_tgt, 'Play Current Clip')]

            if not nav_actions:
                errors.append(f"{bn}: missing {nav_tgt}")
            if not play_actions:
                errors.append(f"{bn}: missing Play Current Clip")
            if play_actions and set(a.get('receiverAtom') for a in play_actions) != leaders:
                errors.append(f"{bn}: Play Current Clip on wrong atoms: {[a.get('receiverAtom') for a in play_actions]}")
            if stray_actions:
                errors.append(f"{bn}: unexpected actions: {[a.get('receiverTargetName') for a in stray_actions]}")

            btn_summary[bn] = [(a.get('receiverAtom'), a.get('receiverTargetName')) for a in starts]

        if errors:
            raise RuntimeError('VERIFY FAILED: ' + '; '.join(errors))

        sz = round(os.path.getsize(var_out)/1024/1024, 1)
        print(f"OK  {os.path.basename(var_out)}  [{sz}MB]  leaders={sorted(leaders)}")
        print(f"    NEXT={btn_summary.get('NEXT')}  PREV={btn_summary.get('PREV')}")
        ok.append(fname)

    except Exception as e:
        import traceback
        print(f"FAIL {fname}: {e}")
        traceback.print_exc()
        fail.append((fname, str(e)))

print(f"\n=== Done: {len(ok)} OK, {len(fail)} FAIL ===")
for f, e in fail:
    print(f"  FAIL: {f}: {e}")
