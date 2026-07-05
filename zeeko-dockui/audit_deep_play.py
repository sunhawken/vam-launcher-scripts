"""
Deep search for:
  1. receiver == plugin#0_VamTimeline.AtomPlugin with any Play target
  2. Any string containing '_Play' anywhere in the scene JSON

Searches ALL atoms/storables recursively.
"""
import zipfile, json, re, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ZEEKO = r"T:\New folder\AddonPackages\cleaned\Zeeko"
COFFY_D = r"T:\New folder\AddonPackages\cleaned"

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)

def find_play_in_obj(obj, path=""):
    """Recursively find all VamTimeline Play actions and _Play strings."""
    results = []
    if isinstance(obj, dict):
        recv = obj.get('receiver', '')
        tgt  = obj.get('receiverTargetName', '')
        recv_atom = obj.get('receiverAtom', '')
        name = obj.get('name', '')
        # VamTimeline + Play
        if recv == 'plugin#0_VamTimeline.AtomPlugin' and 'Play' in tgt:
            results.append(f"VT_Play | atom={recv_atom} | target='{tgt}' | name='{name}' | @ {path}")
        # _Play in name field
        if '_Play' in name or '_play' in name:
            results.append(f"_Play_name | name='{name}' | @ {path}")
        for k, v in obj.items():
            results.extend(find_play_in_obj(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            results.extend(find_play_in_obj(item, f"{path}[{i}]"))
    return results

def pkg_ver(fname):
    base = fname.replace('.DISABLED','').replace('.var','')
    try: return int(base.rsplit('.', 1)[1])
    except: return 0

def pkg_name(fname):
    base = fname.replace('.DISABLED','').replace('.var','')
    return base.rsplit('.', 1)[0]

# Collect ALL files (every version)
all_files = []
for f in sorted(os.listdir(ZEEKO)):
    if (f.endswith('.var') or f.endswith('.DISABLED')) and '.par2' not in f:
        all_files.append(os.path.join(ZEEKO, f))
for f in sorted(os.listdir(COFFY_D)):
    if 'Coffy' in f and (f.endswith('.var') or f.endswith('.DISABLED')) and '.par2' not in f:
        all_files.append(os.path.join(COFFY_D, f))

print(f"Scanning {len(all_files)} files...\n")

for fpath in all_files:
    fname = os.path.basename(fpath)
    try:
        with zipfile.ZipFile(fpath, 'r') as z:
            scene_file = next((n for n in z.namelist() if n.endswith('.json') and 'scene' in n.lower()), None)
            if not scene_file: continue
            raw = fix_json(z.read(scene_file).decode('utf-8-sig', errors='replace'))
        scene = json.loads(raw)
        results = find_play_in_obj(scene)
        if results:
            print(f"\n[{fname}]")
            seen = set()
            for r in results:
                # Deduplicate on target name
                key = r.split('|')[0].strip() + r.split("target='")[1].split("'")[0] if "target='" in r else r[:80]
                if key not in seen:
                    seen.add(key)
                    print(f"  {r}")
        else:
            print(f"[{fname}] -- no Play triggers found")
    except Exception as e:
        print(f"[{fname}] ERROR: {e}")

print("\n=== DONE ===")
