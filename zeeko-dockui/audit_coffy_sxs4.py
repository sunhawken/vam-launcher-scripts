"""
Audit DockedUI button structure in both files.
Show full startActions for NEXT and PREV buttons.
"""
import zipfile, json, re, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FILES = [
    r"T:\New folder\AddonPackages\cleaned\sxs4.50_animations_3.7.DISABLED",
    r"T:\New folder\AddonPackages\cleaned\Coffy.50_animated_sex_loops.3.var",
]

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)

for fpath in FILES:
    fname = os.path.basename(fpath)
    print(f"\n{'='*70}")
    print(f"FILE: {fname}")
    with zipfile.ZipFile(fpath,'r') as z:
        scene_file = next(n for n in z.namelist() if n.endswith('.json') and 'scene' in n.lower())
        raw = fix_json(z.read(scene_file).decode('utf-8-sig','replace'))
    scene = json.loads(raw)

    cc = next((a for a in scene['atoms'] if a.get('id') == 'CoreControl'), None)
    if not cc:
        print("  No CoreControl"); continue

    dk = next((s for s in cc.get('storables',[]) if 'DockedUI' in s.get('id','')), None)
    if not dk:
        print("  No DockedUI"); continue

    print(f"  DockedUI id: {dk.get('id')}")
    cnt = int(dk.get('Count', dk.get('counts','4')))
    print(f"  Button count: {cnt}")

    for i in range(cnt):
        bw = dk.get(f'ButtonWidget{i}', {})
        bn = bw.get('name','')
        ak = bn + str(i)
        entry = dk.get(ak, {})
        starts = entry.get('startActions', [])
        print(f"\n  [{i}] Button='{bn}' key='{ak}'  startActions count={len(starts)}")
        for j, a in enumerate(starts[:10]):
            print(f"    [{j}] name='{a.get('name','')}' atom='{a.get('receiverAtom','')}' target='{a.get('receiverTargetName','')}'")
        if len(starts) > 10:
            print(f"    ... {len(starts)-10} more")

    # Also look at a UIButton to see its trigger pattern in sxs4
    print(f"\n  First 3 UIButton atoms with VT triggers:")
    shown = 0
    for atom in scene.get('atoms',[]):
        if atom.get('type') != 'UIButton': continue
        for s in atom.get('storables',[]):
            starts = s.get('trigger',{}).get('startActions',[])
            if any(a.get('receiver','').endswith('VamTimeline.AtomPlugin') for a in starts):
                print(f"  UIButton '{atom.get('id')}': {[a.get('receiverTargetName','') for a in starts]}")
                shown += 1
                break
        if shown >= 3: break

print("\n=== DONE ===")
