"""
Apply all pending fixes to Coffy.50_animated_sex_loops.5.var -> .6.var:
  1. Strip followers (female) from NEXT/PREV navigation
  2. PLAY button: startActions=Play Current Clip (male), endActions=Stop (male), transitionActions=[]
"""
import zipfile, json, re, os, shutil, subprocess, tempfile, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SEVENZIP   = r"C:\Program Files\7-Zip\7z.exe"
BACKUP_DIR = r"T:\New folder\backup"
COFFY_DIR  = r"T:\New folder\AddonPackages\cleaned"
VT         = "plugin#0_VamTimeline.AtomPlugin"

VAR_IN  = os.path.join(COFFY_DIR, "Coffy.50_animated_sex_loops.5.var")
VAR_OUT = os.path.join(COFFY_DIR, "Coffy.50_animated_sex_loops.6.var")

NAV_TARGETS = {'Next Animation', 'Previous Animation', 'Play Current Clip'}

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)
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
        tmp = os.path.join(tempfile.gettempdir(), '_coffy_all.zip')
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

sf = next(n for n in files if n.endswith('.json') and 'scene' in n.lower())
scene = json.loads(fix_json(files[sf].decode('utf-8-sig','replace')))

# Identify leaders and followers
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

followers = vt_atoms - leaders
print(f"VT atoms: {sorted(vt_atoms)}")
print(f"Leaders:  {sorted(leaders)}")
print(f"Followers:{sorted(followers)}")

cc = next(a for a in scene['atoms'] if a.get('id') == 'CoreControl')
dk = next(s for s in cc['storables'] if 'DockedUI' in s.get('id',''))
cnt = int(dk.get('Count', dk.get('counts','4')))

for i in range(cnt):
    bn = dk.get(f'ButtonWidget{i}',{}).get('name','')
    ak = bn + str(i)

    if bn in ('NEXT','PREV'):
        entry = dk.get(ak, {})
        before = entry.get('startActions', [])
        after = [a for a in before
                 if not (a.get('receiverAtom','') in followers and
                         a.get('receiverTargetName','') in NAV_TARGETS)]
        removed = len(before) - len(after)
        print(f"  {bn}: removed {removed} follower actions, kept {[a.get('receiverTargetName') for a in after]}")
        entry['startActions'] = after
        dk[ak] = entry
        if 'Actions' in dk and ak in dk['Actions']:
            inner = dk['Actions'][ak]
            inner['startActions'] = [a for a in inner.get('startActions',[])
                                      if not (a.get('receiverAtom','') in followers and
                                              a.get('receiverTargetName','') in NAV_TARGETS)]
            dk['Actions'][ak] = inner

    elif bn == 'PLAY':
        new_entry = {
            "displayName": dk.get(ak, {}).get('displayName', 'Play'),
            "startActions": [make_action(f"Play_{l}", l, "Play Current Clip") for l in sorted(leaders)],
            "transitionActions": [],
            "endActions":   [make_action(f"Stop_{l}", l, "Stop") for l in sorted(leaders)],
        }
        dk[ak] = new_entry
        if 'Actions' in dk and ak in dk['Actions']:
            dk['Actions'][ak] = dict(new_entry)
        print(f"  PLAY: start={[(a['receiverAtom'], a['receiverTargetName']) for a in new_entry['startActions']]} "
              f"end={[(a['receiverAtom'], a['receiverTargetName']) for a in new_entry['endActions']]}")

# Update refs
old_ref = "Coffy.50_animated_sex_loops.5"
new_ref = "Coffy.50_animated_sex_loops.6"
if 'LoadPresetPath' in dk:
    dk['LoadPresetPath'] = dk['LoadPresetPath'].replace(old_ref, new_ref)
for ppath in list(files.keys()):
    if 'DockedUIPreset' in ppath:
        files[ppath] = files[ppath].replace(old_ref.encode(), new_ref.encode())

files[sf] = json.dumps(scene, indent=3, ensure_ascii=False).encode('utf-8')
repack(files, VAR_OUT)

# Verify
with zipfile.ZipFile(VAR_OUT) as z:
    raw2 = fix_json(z.read(sf).decode('utf-8-sig','replace'))
s2 = json.loads(raw2)
cc2 = next(a for a in s2['atoms'] if a.get('id') == 'CoreControl')
dk2 = next(s for s in cc2['storables'] if 'DockedUI' in s.get('id',''))
cnt2 = int(dk2.get('Count', dk2.get('counts','0')))
print(f"\nVerify:")
for i in range(cnt2):
    bn = dk2.get(f'ButtonWidget{i}',{}).get('name','')
    ak = bn + str(i)
    e = dk2.get(ak,{})
    sa = [(a.get('receiverAtom'), a.get('receiverTargetName')) for a in e.get('startActions',[])]
    ea = [(a.get('receiverAtom'), a.get('receiverTargetName')) for a in e.get('endActions',[])]
    print(f"  {bn}: start={sa} end={ea}")

sz = round(os.path.getsize(VAR_OUT)/1024/1024, 1)
print(f"\nOK  {os.path.basename(VAR_OUT)}  [{sz}MB]")
os.remove(VAR_IN)
print("Done.")
