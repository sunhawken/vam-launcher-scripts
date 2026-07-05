"""
build_aviana.py — POGVR.Aviana.1 (Slim) → POGVR.AvianaMale.1.var
- UV-convert face diffuse + face normal (both 4096)
- Genitals bake from face skin tone
- Copy Slim Body + Slim Head morphs to male/
- Extract bun front/bang + pony base2/back → Male/ (HairMale)
- Keep Enhanced Eyes clothing + all its storables
- Drop Qing stockings, BreastControl, BreastPhysicsMesh, BreastInOut, FemaleAnatomy, BendFix
- Carry full skin/irises/sclera/lacrimals/teeth/tongue/mouth/eyelash storables
"""
import zipfile, json, os, copy, shutil
import numpy as np
from PIL import Image
from io import BytesIO
from scipy.ndimage import distance_transform_edt, map_coordinates

SRC_PKG   = r'T:\New folder\AddonPackages\superlady-md\POGVR\POGVR.Aviana.1.var'
BUN_PKG   = r'T:\New folder\AddonPackages\non-scene\ddaamm.hair_bun.4.var'
PONY_PKG  = r'T:\New folder\AddonPackages\non-scene\ddaamm.hair_pony.2.var'
UVSWAPPER = r'T:\New folder\AddonPackages\keep\mrmr32.UVSwapper.5.var'
UVDATA    = r'C:\tmp\UVData.json'
STAGE     = r'C:\tmp\aviana_male_v1'
OUT_VAR   = r'T:\New folder\AddonPackages\keep\POGVR.AvianaMale.1.var'
PKG_NAME  = 'POGVR.AvianaMale.1'
TEX_DIR   = 'Custom/Atom/Person/Textures/Aviana'
VAP_SRC   = 'Custom/Atom/Person/Appearance/Preset_Aviana - Thicc.vap'

os.makedirs(STAGE, exist_ok=True)

# ── UV helpers ────────────────────────────────────────────────────────────────
def to_px(uv, W, H):
    return np.stack([uv[:,0]*W, (1.0-uv[:,1])*H], axis=1)

def rasterize_triangle(Dp, Sp, mx, my):
    x0,y0=Dp[0]; x1,y1=Dp[1]; x2,y2=Dp[2]
    sx0,sy0=Sp[0]; sx1,sy1=Sp[1]; sx2,sy2=Sp[2]
    xmin=int(max(0,np.floor(min(x0,x1,x2)))); xmax=int(min(mx.shape[1]-1,np.ceil(max(x0,x1,x2))))
    ymin=int(max(0,np.floor(min(y0,y1,y2)))); ymax=int(min(mx.shape[0]-1,np.ceil(max(y0,y1,y2))))
    denom=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
    if abs(denom)<1e-10: return
    xs=np.arange(xmin,xmax+1,dtype=np.float32)
    for yi in range(ymin,ymax+1):
        w0=((y1-y2)*(xs-x2)+(x2-x1)*(yi-y2))/denom
        w1=((y2-y0)*(xs-x2)+(x0-x2)*(yi-y2))/denom
        w2=1.0-w0-w1
        mask=(w0>=0)&(w1>=0)&(w2>=0)
        for xi in np.where(mask)[0]:
            px=int(xs[xi])
            mx[yi,px]=w0[xi]*sx0+w1[xi]*sx1+w2[xi]*sx2
            my[yi,px]=w0[xi]*sy0+w1[xi]*sy1+w2[xi]*sy2

def build_map(dst_uv, src_uv, mesh, W, H):
    Dp=to_px(dst_uv,W,H); Sp=to_px(src_uv,W,H)
    mx=np.full((H,W),-1.0,np.float32); my=np.full((H,W),-1.0,np.float32)
    N=len(mesh)
    for i,tri in enumerate(mesh):
        if i%(N//10)==0: print(f'  {i}/{N} ({100*i//N}%)')
        rasterize_triangle(Dp[tri],Sp[tri],mx,my)
    filled=mx>=0
    _,idx=distance_transform_edt(~filled,return_indices=True)
    mx=mx[idx[0],idx[1]]; my=my[idx[0],idx[1]]
    return mx, my

def apply_map(img_rgba, mx, my):
    H,W=img_rgba.shape[:2]
    mx_c=np.clip(mx,0,W-1); my_c=np.clip(my,0,H-1)
    out=np.zeros_like(img_rgba)
    for c in range(img_rgba.shape[2]):
        out[:,:,c]=map_coordinates(img_rgba[:,:,c].astype(np.float32),[my_c,mx_c],order=1,mode='nearest')
    return out.astype(np.uint8)

# ── Load UV data ──────────────────────────────────────────────────────────────
print('Loading UVData.json...')
with open(UVDATA,'r') as fh: uvdata=json.load(fh)
regions={}
for name in ['face','torso','limbs']:
    r=uvdata[name]
    regions[name]={
        'male':   np.array([[v['x'],v['y']] for v in r['MaleUVs']],  dtype=np.float32),
        'female': np.array([[v['x'],v['y']] for v in r['FemaleUVs']],dtype=np.float32),
        'mesh':   np.array([[t['d1'],t['d2'],t['d3']] for t in r['Mesh']],dtype=np.int32),
    }

tex_dir=os.path.join(STAGE,TEX_DIR.replace('/',os.sep))
os.makedirs(tex_dir,exist_ok=True)

# ── Build face UV map once, reuse for diffuse + normal ───────────────────────
face_path=os.path.join(tex_dir,'Aviana_face_male.jpg')
norm_path=os.path.join(tex_dir,'NormalMap30_male.jpg')
if os.path.exists(face_path) and os.path.exists(norm_path):
    print('Textures already converted, skipping UV remap.')
else:
    print('\n=== Face UV map 4096 ===')
    r=regions['face']
    mx_f,my_f=build_map(r['male'],r['female'],r['mesh'],4096,4096)
    with zipfile.ZipFile(SRC_PKG,'r') as zsrc:
        print('\n=== Face diffuse ===')
        img=np.array(Image.open(BytesIO(zsrc.read('Custom/Atom/Person/Textures/Aviana/Aviana_face.jpg'))).convert('RGBA'))
        out=apply_map(img,mx_f,my_f)
        Image.fromarray(out[:,:,:3]).save(face_path,quality=92)
        print('  -> Aviana_face_male.jpg')
        print('\n=== Face normal ===')
        img=np.array(Image.open(BytesIO(zsrc.read('Custom/Atom/Person/Textures/Aviana/NormalMap(30).jpg'))).convert('RGBA'))
        out=apply_map(img,mx_f,my_f)
        Image.fromarray(out[:,:,:3]).save(norm_path,quality=92)
        print('  -> NormalMap30_male.jpg')
    del img, out, mx_f, my_f

# ── Genitals bake ─────────────────────────────────────────────────────────────
print('\n=== Genitals bake ===')
with zipfile.ZipFile(UVSWAPPER,'r') as zuv:
    tmpl=np.array(Image.open(BytesIO(zuv.read('Custom/Scripts/mrmr32/UVSwapper/genitals/male/genitalsD.png'))).convert('RGBA'))
    tip =np.array(Image.open(BytesIO(zuv.read('Custom/Scripts/mrmr32/UVSwapper/genitals/male/genitalsD_tip.png'))).convert('RGBA'))

face_img=np.array(Image.open(face_path).convert('RGB'),dtype=np.float32)/255.0
H_f,W_f=face_img.shape[:2]
skin_rgb=face_img[int(0.15*H_f):int(0.55*H_f),int(0.35*W_f):int(0.65*W_f)].reshape(-1,3).mean(0)
print(f'Face skin sample: rgb=({skin_rgb[0]:.3f},{skin_rgb[1]:.3f},{skin_rgb[2]:.3f})')

def rgb_to_hsv(rgb):
    r,g,b=float(rgb[0]),float(rgb[1]),float(rgb[2])
    maxc=max(r,g,b); minc=min(r,g,b); delta=maxc-minc
    v=maxc; s=delta/maxc if maxc>0 else 0.0
    if delta==0: h=0.0
    elif maxc==r: h=((g-b)/delta)%6.0/6.0
    elif maxc==g: h=((b-r)/delta+2)/6.0
    else:         h=((r-g)/delta+4)/6.0
    return np.array([h,s,v])

def hsv_to_rgb(hsv):
    h,s,v=hsv[0],hsv[1],hsv[2]
    if s==0: return np.array([v,v,v])
    i=int(h*6)%6; f=h*6-i; p=v*(1-s); q=v*(1-f*s); t=v*(1-(1-f)*s)
    return [np.array([v,t,p]),np.array([q,v,p]),np.array([p,v,t]),
            np.array([p,q,v]),np.array([t,p,v]),np.array([v,p,q])][i]

REF_OFFSET=np.array([-0.0066,-0.0213,-0.0380])
skin_hsv=rgb_to_hsv(skin_rgb)
target_hsv=np.clip(skin_hsv+REF_OFFSET,[0,0,0],[1,1,1])

H_tm,W_tm=tmpl.shape[:2]
tg_rgb=tmpl[int(0.05*H_tm):int(0.30*H_tm),int(0.30*W_tm):int(0.70*W_tm),:3].reshape(-1,3).astype(np.float32).mean(0)/255.0
tg_hsv=rgb_to_hsv(tg_rgb)
dh=target_hsv[0]-tg_hsv[0]; ds=target_hsv[1]-tg_hsv[1]; dv=target_hsv[2]-tg_hsv[2]
print(f'Target gens HSV: ({target_hsv[0]:.4f},{target_hsv[1]:.4f},{target_hsv[2]:.4f})')
print(f'Apply offset: h={dh:+.4f} s={ds:+.4f} v={dv:+.4f}')

def shift_hsv_image(img_rgba,dh,ds,dv):
    rgb=img_rgba[:,:,:3].astype(np.float32)/255.0
    alpha=img_rgba[:,:,3:4]
    maxc=rgb.max(2,keepdims=True); minc=rgb.min(2,keepdims=True); delta=maxc-minc
    v=np.clip(maxc+dv,0,1)
    s_ch=np.where(maxc>0,delta/(maxc+1e-10),0.0); s=np.clip(s_ch+ds,0,1)
    r=rgb[:,:,0:1]; g=rgb[:,:,1:2]; b=rgb[:,:,2:3]
    h=np.zeros_like(r)
    mask_r=(maxc==r)&(delta>0); mask_g=(maxc==g)&(delta>0)&~mask_r; mask_b=~mask_r&~mask_g&(delta>0)
    h[mask_r]=(((g-b)/(delta+1e-10))[mask_r])%6.0/6.0
    h[mask_g]=(((b-r)/(delta+1e-10))[mask_g]+2)/6.0
    h[mask_b]=(((r-g)/(delta+1e-10))[mask_b]+4)/6.0
    h=np.clip(h+dh,0,1)
    i=(h*6).astype(int)%6; f=h*6-np.floor(h*6)
    p=v*(1-s); q=v*(1-f*s); t=v*(1-(1-f)*s)
    out_r=np.where(i==0,v,np.where(i==1,q,np.where(i==2,p,np.where(i==3,p,np.where(i==4,t,v)))))
    out_g=np.where(i==0,t,np.where(i==1,v,np.where(i==2,v,np.where(i==3,q,np.where(i==4,p,p)))))
    out_b=np.where(i==0,p,np.where(i==1,p,np.where(i==2,t,np.where(i==3,v,np.where(i==4,v,q)))))
    out_rgb=np.clip(np.concatenate([out_r,out_g,out_b],2)*255,0,255).astype(np.uint8)
    return np.concatenate([out_rgb,alpha],2)

gens_shifted=shift_hsv_image(tmpl,dh,ds,dv)
ta=tip[:,:,3:4].astype(np.float32)/255.0
gens_final=(gens_shifted.astype(np.float32)*(1-ta)+tip.astype(np.float32)*ta).astype(np.uint8)
Image.fromarray(gens_final).save(os.path.join(tex_dir,'Aviana_Gens_male.png'))
print('  -> Aviana_Gens_male.png')

# ── Copy Thicc morphs to male/ (remove any stale Slim files) ──────────────────
print('\n=== Copying morphs ===')
morph_dst=os.path.join(STAGE,r'Custom\Atom\Person\Morphs\male')
if os.path.exists(morph_dst):
    shutil.rmtree(morph_dst)
os.makedirs(morph_dst,exist_ok=True)
with zipfile.ZipFile(SRC_PKG,'r') as z:
    for entry in ['Custom/Atom/Person/Morphs/female/Aviana - Thicc - Body.vmb',
                  'Custom/Atom/Person/Morphs/female/Aviana - Thicc - Body.vmi',
                  'Custom/Atom/Person/Morphs/female/Aviana - Thicc - Head.vmb',
                  'Custom/Atom/Person/Morphs/female/Aviana - Thicc - Head.vmi']:
        data=z.read(entry)
        fname=os.path.basename(entry)
        if fname.endswith('.vmi'):
            txt=data.decode('utf-8',errors='replace')
            txt=txt.replace('SELF:/Custom/Atom/Person/Morphs/female/',
                            f'{PKG_NAME}:/Custom/Atom/Person/Morphs/male/')
            data=txt.encode('utf-8')
        with open(os.path.join(morph_dst,fname),'wb') as fh: fh.write(data)
        print(f'  {fname}')

# ── Extract hair items to Male/ paths ─────────────────────────────────────────
print('\n=== Extracting hair to Male/ ===')
HAIR_ITEMS=[
    (BUN_PKG,  'ddaamm.hair_bun.4',  'ddaamm/ddaamm/ddaamm bun front'),
    (BUN_PKG,  'ddaamm.hair_bun.4',  'ddaamm/ddaamm/ddaamm bun bang'),
    (PONY_PKG, 'ddaamm.hair_pony.2', 'ddaamm/ddaamm/ddaamm_pony_base2'),
    (PONY_PKG, 'ddaamm.hair_pony.2', 'ddaamm/ddaamm/ddaamm pony back'),
]
for pkg_path, pkg_id, item in HAIR_ITEMS:
    with zipfile.ZipFile(pkg_path,'r') as z:
        for ext in ['.vam','.vab','.vaj']:
            src=f'Custom/Hair/Female/{item}{ext}'
            data=z.read(src)
            if ext=='.vam':
                d=json.loads(data.decode('utf-8'))
                d['itemType']='HairMale'
                data=json.dumps(d).encode('utf-8')
            if ext=='.vaj':
                txt=data.decode('utf-8')
                if 'SELF:/' in txt:
                    txt=txt.replace('SELF:/',f'{pkg_id}:/')
                    data=txt.encode('utf-8')
            dst_rel=f'Custom/Hair/Male/{item}{ext}'
            dst=os.path.join(STAGE,dst_rel.replace('/',os.sep))
            os.makedirs(os.path.dirname(dst),exist_ok=True)
            with open(dst,'wb') as fh: fh.write(data)
            print(f'  {dst_rel}')

# ── Build preset ──────────────────────────────────────────────────────────────
print('\n=== Building preset ===')
with zipfile.ZipFile(SRC_PKG,'r') as z:
    slim=json.loads(z.read(VAP_SRC))

orig={s['id']:s for s in slim['storables']}

DROP_IDS={'BreastControl','BreastPhysicsMesh','BreastInOut','FemaleAnatomy',
          'BendFix','AutoJawMouthMorph','AutoExpressions'}
DROP_PREFIXES=('Qing:',)

SKIP_MORPH_NAMES={'Nipples','Labia majora-spread-LLow','Labia majora-spread-RLow',
                  'Labia minora-relaxation','Labia minora-size','Labia minora-thickness',
                  'Pubic Area Size'}

P=PKG_NAME

# Geometry
geo=copy.deepcopy(orig['geometry'])
geo['character']='Male Custom'
geo['useFemaleMorphsOnMale']='true'
geo.pop('useMaleMorphsOnFemale',None)
geo.pop('useAuxBreastColliders',None)

# Clothing: Enhanced Eyes + WeebU panty (drop Qing/Tank Top/Shorts)
geo['clothing']=[c for c in geo['clothing']
                 if 'Hunting-Succubus' in c['id'] and 'Enhanced_Eyes' in c['id']]
geo['clothing'].append({
    'id':'WeebU.Futa_panty_hose_v2.2:/Custom/Clothing/Male/WeebU/Panty hose 1/Panty hose 1.vam',
    'internalId':'WeebU:Panty hose 1','enabled':'true'
})

# Hair: 4 items at Male/ PKG paths
geo['hair']=[
    {'id':f'{P}:/Custom/Hair/Male/ddaamm/ddaamm/ddaamm bun front.vam',   'internalId':'ddaamm:ddaamm bun front',   'enabled':'true'},
    {'id':f'{P}:/Custom/Hair/Male/ddaamm/ddaamm/ddaamm bun bang.vam',    'internalId':'ddaamm:ddaamm bun bang',    'enabled':'true'},
    {'id':f'{P}:/Custom/Hair/Male/ddaamm/ddaamm/ddaamm_pony_base2.vam',  'internalId':'ddaamm:ddaamm_pony_base2', 'enabled':'true'},
    {'id':f'{P}:/Custom/Hair/Male/ddaamm/ddaamm/ddaamm pony back.vam',   'internalId':'ddaamm:ddaamm pony back',  'enabled':'true'},
]

# Morphs: Slim Body + Slim Head at male/ paths, skip female-specific
new_morphs=[]
for m in geo.get('morphs',[]):
    uid=m.get('uid',''); name=m.get('name','')
    if 'female_genitalia' in uid: continue
    if name in SKIP_MORPH_NAMES: continue
    m2=copy.deepcopy(m)
    if uid.startswith('SELF:/Custom/Atom/Person/Morphs/female/'):
        m2['uid']=uid.replace('SELF:/Custom/Atom/Person/Morphs/female/',
                              f'{P}:/Custom/Atom/Person/Morphs/male/')
    new_morphs.append(m2)
new_morphs+=[
    {'uid':'MVR_G2Female','name':'MVR_G2Female','value':'1'},
    {'uid':'Michael 6 Body','name':'Michael 6 Body','value':'0'},
    {'uid':'Michael 6 Head','name':'Michael 6 Head','value':'0'},
]
geo['morphs']=new_morphs

# Textures
textures={
    'id':'textures',
    'autoBlendGenitalTextures':               orig['textures'].get('autoBlendGenitalTextures','false'),
    'autoBlendGenitalSpecGlossNormalTextures':orig['textures'].get('autoBlendGenitalSpecGlossNormalTextures','true'),
    'autoBlendGenitalLightenDarken':          orig['textures'].get('autoBlendGenitalLightenDarken','0'),
    'autoBlendGenitalHueOffset':              orig['textures'].get('autoBlendGenitalHueOffset','0'),
    'autoBlendGenitalSaturationOffset':       orig['textures'].get('autoBlendGenitalSaturationOffset','0'),
    'faceDiffuseUrl':     f'{P}:/{TEX_DIR}/Aviana_face_male.jpg',
    'faceNormalUrl':      f'{P}:/{TEX_DIR}/NormalMap30_male.jpg',
    'faceGlossUrl':       '',
    'faceSpecularUrl':    '',
    'faceDecalUrl':       '',
    'torsoDiffuseUrl':    '',
    'torsoNormalUrl':     '',
    'torsoSpecularUrl':   '',
    'torsoDecalUrl':      '',
    'limbsDiffuseUrl':    '',
    'genitalsDiffuseUrl': f'{P}:/{TEX_DIR}/Aviana_Gens_male.png',
    'genitalsNormalUrl':  '',
    'genitalsSpecularUrl':'',
    'genitalsGlossUrl':   '',
    'genitalsDecalUrl':   '',
    'faceDetailUrl':      '',
    'torsoDetailUrl':     '',
    'limbsDetailUrl':     '',
    'genitalsDetailUrl':  '',
}

# Skin: full copy, remove Face/Nails select fields
skin=copy.deepcopy(orig['skin'])
skin.pop('Face',None); skin.pop('Nails',None); skin.pop('Pubic Hair',None)

# Collect all remaining storables in order
new_storables=[geo, textures, skin]

PASSTHROUGH_IDS=['irises','sclera','lacrimals','FemaleEyelashes','MaleEyelashes',
                 'teeth','tongue','mouth','EyelidControl','GluteControl',
                 'LowerPhysicsMesh','SoftBodyPhysicsEnabler','rescaleObject']
for sid in PASSTHROUGH_IDS:
    if sid in orig:
        new_storables.append(copy.deepcopy(orig[sid]))

# Hair + eye storables: all ddaamm:* and HUNTING-SUCCUBUS:* from slim
for s in slim['storables']:
    sid=s['id']
    if sid in DROP_IDS: continue
    if any(sid.startswith(p) for p in DROP_PREFIXES): continue
    if sid in {ss['id'] for ss in new_storables}: continue  # already added
    if sid.startswith('ddaamm:') or sid.startswith('HUNTING-SUCCUBUS:'):
        new_storables.append(copy.deepcopy(s))

# Blanket SELF:/ → PKG_NAME:/ replacement
vap_text=json.dumps({'setUnlistedParamsToDefault':'true','storables':new_storables})
vap_text=vap_text.replace('SELF:/',f'{P}:/')
vap=json.loads(vap_text)

vap_dir=os.path.join(STAGE,r'Custom\Atom\Person\Appearance')
os.makedirs(vap_dir,exist_ok=True)
vap_path=os.path.join(vap_dir,'Preset_Aviana_Male.vap')
with open(vap_path,'w',encoding='utf-8') as fh: json.dump(vap,fh,indent=3)
print(f'  {len(vap["storables"])} storables saved')

# ── meta.json ─────────────────────────────────────────────────────────────────
print('\n=== meta.json ===')
content_list=[]
for root,dirs,files in os.walk(STAGE):
    for fname in files:
        rel=os.path.relpath(os.path.join(root,fname),STAGE).replace(os.sep,'/')
        if rel!='meta.json': content_list.append(rel)
content_list.sort()

meta={
    'licenseType':'PC',
    'creatorName':'POGVR',
    'packageName':'AvianaMale',
    'standardReferenceVersionOption':'Latest',
    'version':1,
    'description':'Aviana (Thicc) converted to male',
    'credits':'Skin by RenVR. Hair by ddaamm. Eyes by Hunting-Succubus.',
    'tags':['male','looks'],
    'promotionalLink':'',
    'programVersion':'1.22.0.3',
    'contentList':content_list,
    'dependencies':{
        'Hunting-Succubus.Enhanced_Eyes.latest': {'licenseType':'CC BY-NC','dependencies':{}},
        'ddaamm.hair_bun.4':  {'licenseType':'CC BY','dependencies':{}},
        'ddaamm.hair_pony.2': {'licenseType':'CC BY','dependencies':{}},
        'WeebU.Futa_panty_hose_v2.2': {'licenseType':'CC BY','dependencies':{}},
    },
}
meta_path=os.path.join(STAGE,'meta.json')
with open(meta_path,'w',encoding='utf-8') as fh: json.dump(meta,fh,indent=3)
print(f'  {len(content_list)} entries')

# ── Repack ────────────────────────────────────────────────────────────────────
print('\nPacking...')
if os.path.exists(OUT_VAR): os.remove(OUT_VAR)
with zipfile.ZipFile(OUT_VAR,'w',zipfile.ZIP_DEFLATED,allowZip64=False) as zout:
    zout.write(meta_path,'meta.json')
    for entry in content_list:
        zout.write(os.path.join(STAGE,entry.replace('/',os.sep)),entry)
size_mb=os.path.getsize(OUT_VAR)/1024/1024
print(f'Done: {OUT_VAR}  ({size_mb:.1f} MB)')
with open(OUT_VAR,'rb') as f: raw=f.read()
print('ZIP64: DETECTED!' if b'PK\x06\x06' in raw else 'ZIP64: OK')
print('\nContentList:')
for e in content_list: print(f'  {e}')
