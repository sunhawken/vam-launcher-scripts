"""
For every package (highest version per pkg) in Zeeko + Coffy:
  1. Recursively scan all atoms/storables for VamTimeline 'Play Anim N' targets
     (excludes 'Play Current Clip')
  2. Add those as extra startActions on NEXT and PREV DockedUI buttons
  3. Save as new version (.var), delete old file

Highest-version-per-package: if both .2.var and .1.DISABLED exist, only process .2.var
"""
import zipfile, json, re, os, shutil, subprocess, tempfile, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SEVENZIP   = r"C:\Program Files\7-Zip\7z.exe"
BACKUP_DIR = r"T:\New folder\backup"
ZEEKO      = r"T:\New folder\AddonPackages\cleaned\Zeeko"
COFFY_DIR  = r"T:\New folder\AddonPackages\cleaned"

VT_PLUGIN      = "plugin#0_VamTimeline.AtomPlugin"
DUI_PLUGIN     = "VamEssentials.DockedUI.6:/Custom/Scripts/VamEssentials/DockedUI/DockedUI.cslist"
DOCKUI_KEY     = "VamEssentials.DockedUI.6"
PRESET_DT_PATH = "Saves/DockedUI/DockedUIPreset_Zeeko DT.json"
PRESET_VR_PATH = "Saves/DockedUI/DockedUIPreset_Zeeko VR.json"

def fix_json(raw): return re.sub(r',(\s*[}\]])', r'\1', raw)

def pkg_name(fname):
    base = fname.replace('.DISABLED','').replace('.var','')
    return base.rsplit('.', 1)[0]

def pkg_ver(fname):
    base = fname.replace('.DISABLED','').replace('.var','')
    try: return int(base.rsplit('.', 1)[1])
    except: return 0

def next_out(fpath, out_dir):
    fname = os.path.basename(fpath)
    pkg   = pkg_name(fname)
    ver   = pkg_ver(fname)
    new_ver = ver + 1
    return os.path.join(out_dir, f"{pkg}.{new_ver}.var"), f"{pkg}.{new_ver}"

def collect_play_anim_actions(obj):
    """Recursively collect all (recv_atom, target) tuples where:
       receiver == VT_PLUGIN  AND  'Play' in target  AND  target != 'Play Current Clip'
    Deduplicates by (recv_atom, target).
    """
    results = []
    seen = set()
    _crawl(obj, results, seen)
    return results

def _crawl(obj, out, seen):
    if isinstance(obj, dict):
        recv = obj.get('receiver','')
        tgt  = obj.get('receiverTargetName','')
        recv_atom = obj.get('receiverAtom','')
        if (recv == VT_PLUGIN and 'Play' in tgt and tgt != 'Play Current Clip'):
            key = (recv_atom, tgt)
            if key not in seen:
                seen.add(key)
                out.append({'receiverAtom': recv_atom, 'target': tgt})
        for v in obj.values():
            _crawl(v, out, seen)
    elif isinstance(obj, list):
        for item in obj:
            _crawl(item, out, seen)

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
        tmp = os.path.join(tempfile.gettempdir(), '_playanim_patch.zip')
        if os.path.exists(tmp): os.remove(tmp)
        r = subprocess.run([SEVENZIP,'a','-tzip','-mx=1',tmp,
                            os.path.join(tmpdir,'*')], capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError('7z: ' + r.stdout[-500:])
        shutil.copy2(tmp, var_out); os.remove(tmp)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# ── Build highest-version-per-package map ────────────────────────────────────
files_map = {}  # pkg -> (ver, fpath, out_dir)

for f in sorted(os.listdir(ZEEKO)):
    if '.par2' in f: continue
    if not (f.endswith('.var') or f.endswith('.DISABLED')): continue
    pkg = pkg_name(f); ver = pkg_ver(f)
    if pkg not in files_map or ver > files_map[pkg][0]:
        files_map[pkg] = (ver, os.path.join(ZEEKO, f), ZEEKO)

for f in sorted(os.listdir(COFFY_DIR)):
    if 'Coffy' not in f or '.par2' in f: continue
    if not (f.endswith('.var') or f.endswith('.DISABLED')): continue
    pkg = pkg_name(f); ver = pkg_ver(f)
    if pkg not in files_map or ver > files_map[pkg][0]:
        files_map[pkg] = (ver, os.path.join(COFFY_DIR, f), COFFY_DIR)

targets = [(v, fp, od) for pkg, (v, fp, od) in sorted(files_map.items())]
print(f"Processing {len(targets)} packages\n")
ok, fail = [], []

for ver, var_in, out_dir in targets:
    fname = os.path.basename(var_in)
    try:
        var_out, pkg_ref = next_out(var_in, out_dir)

        # Backup
        bk = os.path.join(BACKUP_DIR, fname)
        if not os.path.exists(bk): shutil.copy2(var_in, bk)

        with zipfile.ZipFile(var_in, 'r') as z:
            files = {n: z.read(n) for n in z.namelist()}

        scene_file = next((n for n in files if n.endswith('.json')
                           and 'scene' in n.lower()), None)
        if not scene_file: raise RuntimeError('no scene file')

        raw   = fix_json(files[scene_file].decode('utf-8-sig', errors='replace'))
        scene = json.loads(raw)

        # ── Collect all Play Anim N triggers from anywhere in scene ──────────
        play_anims = collect_play_anim_actions(scene)
        if not play_anims:
            raise RuntimeError('no Play Anim N triggers found in scene')

        # ── Find DockedUI storable ────────────────────────────────────────────
        cc = next((a for a in scene['atoms'] if a.get('id') == 'CoreControl'), None)
        if not cc: raise RuntimeError('no CoreControl')

        dk = next((s for s in cc.get('storables',[])
                   if 'VamEssentials.DockedUI' in s.get('id','')), None)
        if not dk: raise RuntimeError('no DockedUI storable (run add-dockui first)')

        slot_m = re.match(r'plugin#(\d+)_', dk['id'])
        slot   = slot_m.group(1) if slot_m else '0'
        count  = int(dk.get('Count', dk.get('counts', '4')))

        # Sort play_anims by (atom, number in target string) for deterministic order
        def sort_key(pa):
            nums = re.findall(r'\d+', pa['target'])
            return (pa['receiverAtom'], int(nums[0]) if nums else 0)
        play_anims.sort(key=sort_key)

        added = {btn: [] for btn in ('NEXT','PREV')}

        for i in range(count):
            btn_widget = dk.get(f'ButtonWidget{i}', {})
            btn_name   = btn_widget.get('name','')
            if btn_name not in ('NEXT','PREV'): continue
            ak = btn_name + str(i)

            entry = dk.get(ak, {})
            start = entry.get('startActions', [])

            # Remove any existing Play Current Clip entries
            start = [a for a in start if a.get('receiverTargetName') != 'Play Current Clip']

            # Remove existing Play Anim entries (we'll re-add from canonical list)
            start = [a for a in start if not
                     (a.get('receiver') == VT_PLUGIN and
                      'Play' in a.get('receiverTargetName','') and
                      a.get('receiverTargetName','') != 'Play Current Clip')]

            # Append Play Anim N actions
            for pa in play_anims:
                label = f"A_{pa['target']}_{pa['receiverAtom']}"
                start.append(make_action(label, pa['receiverAtom'], pa['target']))
                added[btn_name].append(pa['target'])

            entry['startActions'] = start
            dk[ak] = entry

            # Mirror in nested Actions tab
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

        # Update LoadPresetPath
        dk['LoadPresetPath'] = f"{pkg_ref}:/{PRESET_DT_PATH}"

        # ── Rebuild preset files ──────────────────────────────────────────────
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

        # ── Dependency ────────────────────────────────────────────────────────
        meta = json.loads(files['meta.json'].decode('utf-8-sig', errors='replace'))
        meta.setdefault('dependencies',{})[DOCKUI_KEY] = {"licenseType":"CC BY","dependencies":{}}
        files['meta.json'] = json.dumps(meta, indent=2, ensure_ascii=False).encode('utf-8')

        # ── PluginManager ─────────────────────────────────────────────────────
        pm = next((s for s in cc['storables'] if s.get('id') == 'PluginManager'), None)
        if pm is None:
            pm = {"id":"PluginManager","plugins":{}}
            cc['storables'].insert(0, pm)
        pm.setdefault('plugins',{})[f"plugin#{slot}"] = DUI_PLUGIN

        repack(files, var_out)

        # ── Verify ────────────────────────────────────────────────────────────
        with zipfile.ZipFile(var_out) as z:
            raw2 = fix_json(z.read(scene_file).decode('utf-8-sig', errors='replace'))
        s2 = json.loads(raw2)
        cc2 = next(a for a in s2['atoms'] if a.get('id') == 'CoreControl')
        dk2 = next(s for s in cc2['storables'] if 'DockedUI' in s.get('id',''))
        cnt = int(dk2.get('Count', dk2.get('counts','0')))
        v_ok = []
        for i in range(cnt):
            bn = dk2.get(f'ButtonWidget{i}',{}).get('name','')
            if bn not in ('NEXT','PREV'): continue
            ak = bn + str(i)
            tgts = [a.get('receiverTargetName','') for a in dk2.get(ak,{}).get('startActions',[])]
            play_found = [t for t in tgts if 'Play' in t and t != 'Play Current Clip']
            if not play_found:
                raise RuntimeError(f"{bn} has no Play Anim triggers in output, got: {tgts}")
            v_ok.append(f"{bn}({len(play_found)}✓)")

        sz = round(os.path.getsize(var_out)/1024/1024, 1)
        n_unique = len(play_anims)
        print(f"OK  {fname} -> {os.path.basename(var_out)}  [{sz}MB]  "
              f"PlayAnim={n_unique}  {' '.join(v_ok)}")
        ok.append(fname)

        # Delete old file
        os.remove(var_in)

    except Exception as e:
        import traceback
        print(f"FAIL {fname}: {e}")
        traceback.print_exc()
        fail.append((fname, str(e)))

print(f"\n=== Done: {len(ok)} OK, {len(fail)} FAIL ===")
for f, e in fail: print(f"  FAIL: {f}: {e}")
