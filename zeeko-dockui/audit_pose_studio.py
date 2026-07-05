import zipfile, json, re, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ZEEKO = r"T:\New folder\AddonPackages\cleaned\Zeeko"
VT_PLUGIN = "plugin#0_VamTimeline.AtomPlugin"

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)

def crawl(obj, path, hits):
    if isinstance(obj, dict):
        recv = obj.get('receiver','')
        tgt  = obj.get('receiverTargetName','')
        name = obj.get('name','')
        if recv == VT_PLUGIN:
            hits.append(f"VT | recv_atom={obj.get('receiverAtom','')} target='{tgt}' name='{name}' @ {path}")
        if '_Play' in name or '_play' in name:
            hits.append(f"_Play_name | name='{name}' @ {path}")
        for k, v in obj.items():
            crawl(v, f"{path}.{k}", hits)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            crawl(item, f"{path}[{i}]", hits)

for fname in ["Zeeko.POSE_STUDIO_P1.2.var", "Zeeko.POSE_STUDIO_P2.2.var"]:
    fpath = os.path.join(ZEEKO, fname)
    print(f"\n{'='*60}")
    print(f"FILE: {fname}")
    try:
        with zipfile.ZipFile(fpath,'r') as z:
            names = z.namelist()
            scene_file = next((n for n in names if n.endswith('.json') and 'scene' in n.lower()), None)
            print(f"  scene_file: {scene_file}")
            raw = fix_json(z.read(scene_file).decode('utf-8-sig','replace'))
        scene = json.loads(raw)
        hits = []
        crawl(scene, "root", hits)
        if hits:
            seen = set()
            for h in hits:
                key = h[:120]
                if key not in seen:
                    seen.add(key)
                    print(f"  {h}")
        else:
            print("  -- NO VamTimeline or _Play hits found --")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()

print("\n=== DONE ===")
