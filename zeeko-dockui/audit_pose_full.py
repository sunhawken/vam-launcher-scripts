"""
Show the full action objects for UIButton atoms in POSE_STUDIO files.
"""
import zipfile, json, re, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ZEEKO = r"T:\New folder\AddonPackages\cleaned\Zeeko"
VT_PLUGIN = "plugin#0_VamTimeline.AtomPlugin"

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)

for fname in ["Zeeko.POSE_STUDIO_P1.2.var", "Zeeko.POSE_STUDIO_P2.2.var"]:
    fpath = os.path.join(ZEEKO, fname)
    print(f"\n{'='*60}")
    print(f"FILE: {fname}")
    with zipfile.ZipFile(fpath,'r') as z:
        scene_file = next(n for n in z.namelist() if n.endswith('.json') and 'scene' in n.lower())
        raw = fix_json(z.read(scene_file).decode('utf-8-sig','replace'))
    scene = json.loads(raw)

    # Show first 3 UIButton atoms that have VT triggers
    shown = 0
    for atom in scene.get('atoms', []):
        if atom.get('type') not in ('UIButton', 'UIText'): continue
        for s in atom.get('storables', []):
            trigger = s.get('trigger', {})
            starts = trigger.get('startActions', [])
            vt_actions = [a for a in starts if a.get('receiver') == VT_PLUGIN]
            if vt_actions:
                print(f"\n  Atom '{atom['id']}' (type={atom['type']}):")
                for a in vt_actions:
                    print(f"    {json.dumps(a)}")
                shown += 1
                if shown >= 3: break
        if shown >= 3: break

    # Also show what the DockedUI PREV/NEXT buttons currently have
    cc = next((a for a in scene['atoms'] if a.get('id') == 'CoreControl'), None)
    dk = next((s for s in cc.get('storables',[]) if 'DockedUI' in s.get('id','')), None)
    if dk:
        print(f"\n  DockedUI current button actions:")
        cnt = int(dk.get('Count', dk.get('counts','4')))
        for i in range(cnt):
            bn = dk.get(f'ButtonWidget{i}',{}).get('name','')
            if bn not in ('NEXT','PREV'): continue
            ak = bn + str(i)
            entry = dk.get(ak, {})
            starts = entry.get('startActions', [])
            print(f"  {bn}: {[a.get('receiverTargetName','') for a in starts]}")
    else:
        print("  No DockedUI found")

print("\n=== DONE ===")
