"""
For each Zeeko .var, identify:
- Which atoms have VamTimeline (all VT atoms)
- Which get Play Anim N from UIButtons (leaders)
- Which don't (followers)
- Current PLAY/NEXT/PREV button actions
"""
import zipfile, json, re, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ZEEKO = r"T:\New folder\AddonPackages\cleaned\Zeeko"
VT = "plugin#0_VamTimeline.AtomPlugin"
SKIP = {"Zeeko.POSE_STUDIO_P1", "Zeeko.POSE_STUDIO_P2"}

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)
def pkg_name(f): return f.replace('.DISABLED','').replace('.var','').rsplit('.',1)[0]

for fname in sorted(os.listdir(ZEEKO)):
    if not fname.endswith('.var') or '.par2' in fname: continue
    if pkg_name(fname) in SKIP: continue
    fpath = os.path.join(ZEEKO, fname)
    try:
        with zipfile.ZipFile(fpath,'r') as z:
            sf = next(n for n in z.namelist() if n.endswith('.json') and 'scene' in n.lower())
            raw = fix_json(z.read(sf).decode('utf-8-sig','replace'))
        scene = json.loads(raw)

        # VT atoms
        vt_atoms = set()
        for atom in scene.get('atoms',[]):
            for s in atom.get('storables',[]):
                if s.get('id') == VT:
                    vt_atoms.add(atom['id'])

        # Leader atoms = get Play Anim N from UIButtons
        leaders = set()
        for atom in scene.get('atoms',[]):
            if atom.get('type') != 'UIButton': continue
            for s in atom.get('storables',[]):
                for a in s.get('trigger',{}).get('startActions',[]):
                    if a.get('receiver') == VT and 'Play' in a.get('receiverTargetName','') \
                            and a.get('receiverTargetName') != 'Play Current Clip':
                        leaders.add(a.get('receiverAtom',''))

        followers = vt_atoms - leaders

        # PLAY/NEXT/PREV current actions
        cc = next((a for a in scene['atoms'] if a.get('id') == 'CoreControl'), None)
        dk = next((s for s in cc['storables'] if 'DockedUI' in s.get('id','')), None) if cc else None
        btn_summary = {}
        if dk:
            cnt = int(dk.get('Count', dk.get('counts','4')))
            for i in range(cnt):
                bn = dk.get(f'ButtonWidget{i}',{}).get('name','')
                if bn not in ('PLAY','NEXT','PREV'): continue
                ak = bn + str(i)
                starts = dk.get(ak,{}).get('startActions',[])
                btn_summary[bn] = [(a.get('receiverAtom',''), a.get('receiverTargetName','')) for a in starts]

        print(f"{fname}")
        print(f"  VT atoms:  {sorted(vt_atoms)}")
        print(f"  leaders:   {sorted(leaders)}")
        print(f"  followers: {sorted(followers)}")
        for bn in ('PLAY','NEXT','PREV'):
            if bn in btn_summary:
                print(f"  {bn}: {btn_summary[bn]}")
        print()
    except Exception as e:
        print(f"ERROR {fname}: {e}")

print("=== DONE ===")
