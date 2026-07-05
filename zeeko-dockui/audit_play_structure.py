"""
Dump the full PLAY button entry (all keys) from one Zeeko file and one sxs4 file.
Also dump all VamTimeline receiverTargetName values found anywhere in the scene.
"""
import zipfile, json, re, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FILES = [
    r"T:\New folder\AddonPackages\cleaned\Zeeko\Zeeko.THE_SMASHER_3.6.var",
    r"T:\New folder\AddonPackages\cleaned\sxs4.50_animations_3.7.DISABLED",
]
VT = "plugin#0_VamTimeline.AtomPlugin"

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)

for fpath in FILES:
    fname = os.path.basename(fpath)
    print(f"\n{'='*70}")
    print(f"FILE: {fname}")
    with zipfile.ZipFile(fpath,'r') as z:
        sf = next(n for n in z.namelist() if n.endswith('.json') and 'scene' in n.lower())
        raw = fix_json(z.read(sf).decode('utf-8-sig','replace'))
    scene = json.loads(raw)

    cc = next(a for a in scene['atoms'] if a.get('id') == 'CoreControl')
    dk = next(s for s in cc['storables'] if 'DockedUI' in s.get('id',''))
    cnt = int(dk.get('Count', dk.get('counts','4')))

    # Full dump of PLAY button
    for i in range(cnt):
        bn = dk.get(f'ButtonWidget{i}',{}).get('name','')
        if bn != 'PLAY': continue
        ak = bn + str(i)
        entry = dk.get(ak, {})
        print(f"\n  PLAY entry (key='{ak}') all keys: {list(entry.keys())}")
        print(f"  Full PLAY entry:\n{json.dumps(entry, indent=4)}")
        if 'Actions' in dk and ak in dk['Actions']:
            print(f"\n  Actions tab PLAY:\n{json.dumps(dk['Actions'][ak], indent=4)}")

    # All unique VamTimeline target names used anywhere in scene
    all_targets = set()
    def crawl(obj):
        if isinstance(obj, dict):
            if obj.get('receiver') == VT:
                all_targets.add(obj.get('receiverTargetName',''))
            for v in obj.values(): crawl(v)
        elif isinstance(obj, list):
            for item in obj: crawl(item)
    crawl(scene)
    print(f"\n  All VT receiverTargetNames in scene:")
    for t in sorted(all_targets):
        print(f"    '{t}'")

print("\n=== DONE ===")
