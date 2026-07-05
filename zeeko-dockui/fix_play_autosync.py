"""
Patch PLAY button on all Zeeko .var files:
  Add Stop And Reset on each follower atom BEFORE Play Current Clip on leader.
  Order: Stop And Reset (follower1), Stop And Reset (follower2...), Play Current Clip (leader)
  This resets followers to sync-ready state, then leader starts and followers lock on via SyncWithPeers.
"""
import zipfile, json, re, os, shutil, subprocess, tempfile, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SEVENZIP   = r"C:\Program Files\7-Zip\7z.exe"
BACKUP_DIR = r"T:\New folder\backup"
ZEEKO      = r"T:\New folder\AddonPackages\cleaned\Zeeko"
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
        tmp = os.path.join(tempfile.gettempdir(), '_autosync_fix.zip')
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

        # Leaders from UIButton Play Anim N targets
        vt_atoms = set()
        for atom in scene.get('atoms',[]):
            for s in atom.get('storables',[]):
                if s.get('id') == VT:
                    vt_atoms.add(atom['id'])

        leaders = set()
        for atom in scene.get('atoms',[]):
            if atom.get('type') != 'UIButton': continue
            for s in atom.get('storables',[]):
                for a in s.get('trigger',{}).get('startActions',[]):
                    if (a.get('receiver') == VT and
                            'Play' in a.get('receiverTargetName','') and
                            a.get('receiverTargetName') != 'Play Current Clip'):
                        leaders.add(a.get('receiverAtom',''))

        followers = sorted(vt_atoms - leaders)
        if not followers:
            print(f"SKIP {fname}  (no followers)")
            ok.append(fname + ' [no-followers]')
            continue

        cc = next(a for a in scene['atoms'] if a.get('id') == 'CoreControl')
        dk = next(s for s in cc['storables'] if 'DockedUI' in s.get('id',''))
        cnt = int(dk.get('Count', dk.get('counts','4')))

        patched = False
        for i in range(cnt):
            bn = dk.get(f'ButtonWidget{i}',{}).get('name','')
            if bn != 'PLAY': continue
            ak = bn + str(i)

            entry = dk.get(ak, {})
            existing = entry.get('startActions', [])

            # Don't add if Stop And Reset already present for followers
            follower_resets_present = {
                a.get('receiverAtom') for a in existing
                if a.get('receiverTargetName') == 'Stop And Reset'
                   and a.get('receiverAtom') in followers
            }
            followers_needing_reset = [f for f in followers if f not in follower_resets_present]

            if not followers_needing_reset:
                print(f"SKIP {fname}  (Stop And Reset already present for all followers)")
                patched = None  # sentinel
                break

            # Build new action list: Stop And Reset per follower first, then existing Play actions
            reset_actions = [make_action(f"Sync_{f}", f, "Stop And Reset")
                             for f in followers_needing_reset]
            entry['startActions'] = reset_actions + existing
            dk[ak] = entry

            # Mirror in Actions tab
            if 'Actions' in dk and ak in dk['Actions']:
                inner = dk['Actions'][ak]
                inner['startActions'] = reset_actions + inner.get('startActions', [])
                dk['Actions'][ak] = inner

            patched = True

        if patched is None:
            ok.append(fname + ' [already-synced]')
            continue
        if not patched:
            raise RuntimeError('PLAY button not found')

        old_ref = f"{pkg}.{ver}"
        new_ref = f"{pkg}.{ver+1}"
        if 'LoadPresetPath' in dk:
            dk['LoadPresetPath'] = dk['LoadPresetPath'].replace(old_ref, new_ref)
        for ppath in list(files.keys()):
            if 'DockedUIPreset' in ppath:
                files[ppath] = files[ppath].replace(old_ref.encode(), new_ref.encode())

        files[sf] = json.dumps(scene, indent=3, ensure_ascii=False).encode('utf-8')
        repack(files, var_out)

        # Verify
        with zipfile.ZipFile(var_out) as z:
            raw2 = fix_json(z.read(sf).decode('utf-8-sig','replace'))
        s2 = json.loads(raw2)
        cc2 = next(a for a in s2['atoms'] if a.get('id') == 'CoreControl')
        dk2 = next(s for s in cc2['storables'] if 'DockedUI' in s.get('id',''))
        cnt2 = int(dk2.get('Count', dk2.get('counts','0')))
        for i in range(cnt2):
            bn = dk2.get(f'ButtonWidget{i}',{}).get('name','')
            if bn != 'PLAY': continue
            ak = bn + str(i)
            starts = dk2.get(ak,{}).get('startActions',[])
            summary = [(a.get('receiverAtom',''), a.get('receiverTargetName','')) for a in starts]
            print(f"  PLAY verified: {summary}")

        sz = round(os.path.getsize(var_out)/1024/1024, 1)
        print(f"OK  {fname} -> {os.path.basename(var_out)}  [{sz}MB]  followers={followers}")
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
