"""
Process Zeeko.THE_SMASHER_41.2.DISABLED -> Zeeko.THE_SMASHER_41.3.var
Add Play Anim N triggers to NEXT and PREV DockedUI buttons.
"""
import zipfile, json, re, os, shutil, subprocess, tempfile, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SEVENZIP   = r"C:\Program Files\7-Zip\7z.exe"
BACKUP_DIR = r"T:\New folder\backup"
ZEEKO      = r"T:\New folder\AddonPackages\cleaned\Zeeko"

VT_PLUGIN  = "plugin#0_VamTimeline.AtomPlugin"
DUI_PLUGIN = "VamEssentials.DockedUI.6:/Custom/Scripts/VamEssentials/DockedUI/DockedUI.cslist"
DOCKUI_KEY = "VamEssentials.DockedUI.6"
PRESET_DT_PATH = "Saves/DockedUI/DockedUIPreset_Zeeko DT.json"
PRESET_VR_PATH = "Saves/DockedUI/DockedUIPreset_Zeeko VR.json"

VAR_IN  = os.path.join(ZEEKO, "Zeeko.THE_SMASHER_41.2.DISABLED")
VAR_OUT = os.path.join(ZEEKO, "Zeeko.THE_SMASHER_41.3.var")
PKG_REF = "Zeeko.THE_SMASHER_41.3"

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)

def collect_play_anim_actions(obj):
    results = []; seen = set()
    _crawl(obj, results, seen)
    return results

def _crawl(obj, out, seen):
    if isinstance(obj, dict):
        recv = obj.get('receiver','')
        tgt  = obj.get('receiverTargetName','')
        recv_atom = obj.get('receiverAtom','')
        if recv == VT_PLUGIN and 'Play' in tgt and tgt != 'Play Current Clip':
            key = (recv_atom, tgt)
            if key not in seen:
                seen.add(key); out.append({'receiverAtom': recv_atom, 'target': tgt})
        for v in obj.values(): _crawl(v, out, seen)
    elif isinstance(obj, list):
        for item in obj: _crawl(item, out, seen)

def make_action(label, atom, target):
    return {"name": label, "receiverAtom": atom,
            "receiver": VT_PLUGIN, "receiverTargetName": target}

def repack(files, var_out):
    tmpdir = tempfile.mkdtemp()
    try:
        for rel, data in files.items():
            if rel.endswith('/'): continue
            dst = os.path.join(tmpdir, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f: f.write(data)
        tmp = os.path.join(tempfile.gettempdir(), '_smasher41_patch.zip')
        if os.path.exists(tmp): os.remove(tmp)
        r = subprocess.run([SEVENZIP,'a','-tzip','-mx=1',tmp,
                            os.path.join(tmpdir,'*')], capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError('7z: ' + r.stdout[-500:])
        shutil.copy2(tmp, var_out); os.remove(tmp)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# Backup
bk = os.path.join(BACKUP_DIR, os.path.basename(VAR_IN))
if not os.path.exists(bk):
    shutil.copy2(VAR_IN, bk)
    print(f"Backed up to {bk}")
else:
    print(f"Backup already exists: {bk}")

with zipfile.ZipFile(VAR_IN, 'r') as z:
    files = {n: z.read(n) for n in z.namelist()}

scene_file = next((n for n in files if n.endswith('.json') and 'scene' in n.lower()), None)
print(f"Scene file: {scene_file}")

raw   = fix_json(files[scene_file].decode('utf-8-sig', errors='replace'))
scene = json.loads(raw)

play_anims = collect_play_anim_actions(scene)
print(f"Found {len(play_anims)} Play Anim triggers:")
for pa in play_anims:
    print(f"  {pa['receiverAtom']} -> {pa['target']}")

if not play_anims:
    print("ERROR: No Play Anim triggers found!")
    sys.exit(1)

# Sort by (atom, numeric order)
def sort_key(pa):
    nums = re.findall(r'\d+', pa['target'])
    return (pa['receiverAtom'], int(nums[0]) if nums else 0)
play_anims.sort(key=sort_key)

cc = next((a for a in scene['atoms'] if a.get('id') == 'CoreControl'), None)
if not cc: raise RuntimeError('no CoreControl')

dk = next((s for s in cc.get('storables',[])
           if 'VamEssentials.DockedUI' in s.get('id','')), None)
if not dk: raise RuntimeError('no DockedUI storable')

slot_m = re.match(r'plugin#(\d+)_', dk['id'])
slot   = slot_m.group(1) if slot_m else '0'
count  = int(dk.get('Count', dk.get('counts', '4')))

added = {}
for i in range(count):
    btn_widget = dk.get(f'ButtonWidget{i}', {})
    btn_name   = btn_widget.get('name','')
    if btn_name not in ('NEXT','PREV'): continue
    ak = btn_name + str(i)

    entry = dk.get(ak, {})
    start = entry.get('startActions', [])

    # Remove Play Current Clip and existing Play Anim entries
    start = [a for a in start if a.get('receiverTargetName') != 'Play Current Clip']
    start = [a for a in start if not
             (a.get('receiver') == VT_PLUGIN and
              'Play' in a.get('receiverTargetName','') and
              a.get('receiverTargetName','') != 'Play Current Clip')]

    # Append Play Anim N actions
    for pa in play_anims:
        label = f"A_{pa['target']}_{pa['receiverAtom']}"
        start.append(make_action(label, pa['receiverAtom'], pa['target']))

    entry['startActions'] = start
    dk[ak] = entry
    added[btn_name] = len(play_anims)

    # Mirror in Actions tab
    if 'Actions' in dk and ak in dk['Actions']:
        inner = dk['Actions'][ak]
        inner_start = [a for a in inner.get('startActions',[])
                       if not (a.get('receiver') == VT_PLUGIN and
                               'Play' in a.get('receiverTargetName',''))]
        for pa in play_anims:
            label = f"A_{pa['target']}_{pa['receiverAtom']}"
            inner_start.append(make_action(label, pa['receiverAtom'], pa['target']))
        inner['startActions'] = inner_start
        dk['Actions'][ak] = inner

print(f"Updated buttons: {added}")

dk['LoadPresetPath'] = f"{PKG_REF}:/{PRESET_DT_PATH}"

# Rebuild presets
actions_tab = dk.get('Actions', {})
TEXT_TAB = {"font":"Kaushan Script","bold":"false","italic":"false",
            "fontSizeDesktop":"16","fontSizeVR":"30","textAlpha":"1",
            "textColorH":"0.09613234","textColorS":"1","textColorV":"1",
            "alignment":"Center",
            "padTop":"0","padBottom":"0","padLeft":"0","padRight":"0"}
BG_TAB   = {"bgAlpha":"1","bgColorH":"0","bgColorS":"0","bgColorV":"0.3936413",
            "imageDisplayMode":"Stretched","imagePaths":{}}
preset   = {
    "VRMode":"false",
    "MainTab":    {"hotkey":"Escape","InvisibleReveal":"false",
                   "AutoHideWhenUnfreeze":"false","AutoHideWhenMenuClosed":"false",
                   "InactivityTimeout":"5"},
    "TextTab":    TEXT_TAB,
    "BackgroundTab": BG_TAB,
    "OnClickTab": {"useOnClick":"true","highlightIntensity":"0.4999999",
                   "onClickColorR":"0","onClickColorG":"0.8930554",
                   "onClickColorB":"0.9518457"},
    "DesktopTab": {"uiScale":"1","isHorizontal":"true","spacing":"0.03",
                   "width":"-10","height":"40","posX":"1","posY":"0.99","posZ":"0"},
    "VRTab":      {"uiScale":"1","anchorMode":"World Center","atom":"[CameraRig]",
                   "bodyPart":"None","smoothTracking":"false","rotateToUser":"true",
                   "isHorizontal":"false","spacing":"70","width":"120","height":"60",
                   "posX":"0","posY":"0","posZ":"0",
                   "rotX":"0","rotY":"0","rotZ":"0"},
    "ActionsTab": actions_tab,
}
files[PRESET_DT_PATH] = json.dumps(preset, indent=2, ensure_ascii=False).encode('utf-8')
files[PRESET_VR_PATH] = json.dumps(preset, indent=2, ensure_ascii=False).encode('utf-8')
files[scene_file]     = json.dumps(scene, indent=3, ensure_ascii=False).encode('utf-8')

# Dependency
meta = json.loads(files['meta.json'].decode('utf-8-sig', errors='replace'))
meta.setdefault('dependencies',{})[DOCKUI_KEY] = {"licenseType":"CC BY","dependencies":{}}
files['meta.json'] = json.dumps(meta, indent=2, ensure_ascii=False).encode('utf-8')

# PluginManager
pm = next((s for s in cc['storables'] if s.get('id') == 'PluginManager'), None)
if pm is None:
    pm = {"id":"PluginManager","plugins":{}}
    cc['storables'].insert(0, pm)
pm.setdefault('plugins',{})[f"plugin#{slot}"] = DUI_PLUGIN

repack(files, VAR_OUT)

# Verify
with zipfile.ZipFile(VAR_OUT) as z:
    raw2 = fix_json(z.read(scene_file).decode('utf-8-sig', errors='replace'))
s2 = json.loads(raw2)
cc2 = next(a for a in s2['atoms'] if a.get('id') == 'CoreControl')
dk2 = next(s for s in cc2['storables'] if 'DockedUI' in s.get('id',''))
cnt = int(dk2.get('Count', dk2.get('counts','0')))
for i in range(cnt):
    bn = dk2.get(f'ButtonWidget{i}',{}).get('name','')
    if bn not in ('NEXT','PREV'): continue
    ak = bn + str(i)
    tgts = [a.get('receiverTargetName','') for a in dk2.get(ak,{}).get('startActions',[])]
    play_found = [t for t in tgts if 'Play' in t and t != 'Play Current Clip']
    if not play_found:
        raise RuntimeError(f"{bn} has no Play Anim triggers in output!")
    print(f"  {bn}: {len(play_found)} Play Anim triggers verified")

sz = round(os.path.getsize(VAR_OUT)/1024/1024, 1)
print(f"\nOK  {os.path.basename(VAR_OUT)}  [{sz}MB]  PlayAnim={len(play_anims)}")
print("Deleting source .DISABLED...")
os.remove(VAR_IN)
print("Done.")
