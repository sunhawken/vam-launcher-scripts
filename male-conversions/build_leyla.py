"""
build_leyla.py — caelryn.Leyla.6 → caelryn.LeylaMale.1.var
Three appearance presets (L/M/S) + four clothing presets.
ALL clothing kept. VL_13 Shorts_M copied to Male/ path + ClothingMale.
WeebU panty added.
"""
import zipfile, json, os, copy, shutil
import numpy as np
from PIL import Image
from io import BytesIO
from scipy.ndimage import distance_transform_edt, map_coordinates

SRC_PKG    = r'T:\New folder\AddonPackages\superlady-md\caelryn\caelryn.Leyla.6.var'
LONG10     = r'T:\New folder\AddonPackages\non-scene\ddaamm.hair_long10.4.var'
UVSWAPPER  = r'T:\New folder\AddonPackages\keep\mrmr32.UVSwapper.5.var'
IAIFOX_PKG = r'T:\New folder\AddonPackages\non-scene\IAmAFox.Simple_Anklet_Chains.1.var'
GIALLONE_PKG=r'T:\New folder\AddonPackages\non-scene\Giallone.Waist_Chain.1.var'
MARU01_PKG = r'T:\New folder\AddonPackages\superlady-md\maru01\maru01.flower_lei.1.var'
JACKAROO_PKG=r'T:\New folder\AddonPackages\keep\Jackaroo.New_Mouth_Female.7.var'
SKYNETF_PKG= r'T:\New folder\AddonPackages\non-scene\Skynet.Fingernails_HD.2.var'
SKYNETT_PKG= r'T:\New folder\AddonPackages\extra\Skynet.toenails_HD.3.var'
XXXA_PKG   = r'T:\New folder\AddonPackages\extra\xxxa.EyeSDW.3.var'
UVDATA   = r'C:\tmp\UVData.json'
STAGE    = r'C:\tmp\leyla_male_v1'
OUT_VAR  = r'T:\New folder\AddonPackages\keep\caelryn.LeylaMale.2.var'
PKG_NAME = 'caelryn.LeylaMale.2'
TEX_DIR  = 'Custom/Atom/Person/Textures/Leyla'
P        = PKG_NAME

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
    return mx[idx[0],idx[1]], my[idx[0],idx[1]]

def apply_map(img_rgba, mx, my):
    H,W=img_rgba.shape[:2]
    mx_c=np.clip(mx,0,W-1); my_c=np.clip(my,0,H-1)
    out=np.zeros_like(img_rgba)
    for c in range(img_rgba.shape[2]):
        out[:,:,c]=map_coordinates(img_rgba[:,:,c].astype(np.float32),[my_c,mx_c],order=1,mode='nearest')
    return out.astype(np.uint8)

def save_jpg(arr, path, q=92):
    Image.fromarray(arr[:,:,:3]).save(path, quality=q)

def save_png(arr, path):
    Image.fromarray(arr).save(path)

# ── Load UV regions ───────────────────────────────────────────────────────────
print('Loading UVData...')
with open(UVDATA,'r') as fh: uvdata=json.load(fh)
regions={}
for name in ['face','torso','limbs']:
    r=uvdata[name]
    regions[name]={
        'male':  np.array([[v['x'],v['y']] for v in r['MaleUVs']],  dtype=np.float32),
        'female':np.array([[v['x'],v['y']] for v in r['FemaleUVs']],dtype=np.float32),
        'mesh':  np.array([[t['d1'],t['d2'],t['d3']] for t in r['Mesh']],dtype=np.int32),
    }

tex_dst=os.path.join(STAGE,TEX_DIR.replace('/',os.sep))
os.makedirs(tex_dst,exist_ok=True)

# ── UV conversions (skip if already done) ─────────────────────────────────────
face_path=os.path.join(tex_dst,'Face_male.jpg')
if os.path.exists(face_path) and os.path.exists(os.path.join(tex_dst,'Limbs_male.jpg')):
    print('Textures already converted, skipping.')
else:
    def load_tex(zf, name):
        return np.array(Image.open(BytesIO(zf.read(f'Custom/Atom/Person/Textures/Leyla/{name}'))).convert('RGBA'))
    with zipfile.ZipFile(SRC_PKG,'r') as zsrc:
        print('\n=== Face UV 8K ===')
        r=regions['face']
        mx_f8,my_f8=build_map(r['male'],r['female'],r['mesh'],8192,8192)
        mx_f4=mx_f8[::2,::2]/2.0; my_f4=my_f8[::2,::2]/2.0
        save_jpg(apply_map(load_tex(zsrc,'Face.jpg'),mx_f8,my_f8), face_path)
        save_jpg(apply_map(load_tex(zsrc,'Face_n.jpg'),mx_f8,my_f8), os.path.join(tex_dst,'Face_n_male.jpg'))
        save_jpg(apply_map(load_tex(zsrc,'face_G.jpg'),mx_f4,my_f4), os.path.join(tex_dst,'face_G_male.jpg'))
        save_jpg(apply_map(load_tex(zsrc,'Face_s.jpg'),mx_f4,my_f4), os.path.join(tex_dst,'Face_s_male.jpg'))
        del mx_f8,my_f8,mx_f4,my_f4
        print('\n=== Torso UV 8K ===')
        r=regions['torso']
        mx_t8,my_t8=build_map(r['male'],r['female'],r['mesh'],8192,8192)
        mx_t4=mx_t8[::2,::2]/2.0; my_t4=my_t8[::2,::2]/2.0
        save_jpg(apply_map(load_tex(zsrc,'Torso.jpg'),mx_t8,my_t8), os.path.join(tex_dst,'Torso_male.jpg'))
        save_jpg(apply_map(load_tex(zsrc,'Torso_n.jpg'),mx_t8,my_t8), os.path.join(tex_dst,'Torso_n_male.jpg'))
        save_png(apply_map(load_tex(zsrc,'Decal_Tanlines_Torso.png'),mx_t4,my_t4), os.path.join(tex_dst,'Decal_Tanlines_Torso_male.png'))
        del mx_t8,my_t8,mx_t4,my_t4
        print('\n=== Limbs UV 8K ===')
        r=regions['limbs']
        mx_l8,my_l8=build_map(r['male'],r['female'],r['mesh'],8192,8192)
        save_jpg(apply_map(load_tex(zsrc,'Limbs.jpg'),mx_l8,my_l8), os.path.join(tex_dst,'Limbs_male.jpg'))
        save_jpg(apply_map(load_tex(zsrc,'Limbs_n.jpg'),mx_l8,my_l8), os.path.join(tex_dst,'Limbs_n_male.jpg'))
        del mx_l8,my_l8
    print('UV done.')

# ── Genitals bake ─────────────────────────────────────────────────────────────
print('\n=== Genitals bake ===')
with zipfile.ZipFile(UVSWAPPER,'r') as zuv:
    tmpl=np.array(Image.open(BytesIO(zuv.read('Custom/Scripts/mrmr32/UVSwapper/genitals/male/genitalsD.png'))).convert('RGBA'))
    tip =np.array(Image.open(BytesIO(zuv.read('Custom/Scripts/mrmr32/UVSwapper/genitals/male/genitalsD_tip.png'))).convert('RGBA'))

face_arr=np.array(Image.open(face_path).convert('RGB'),dtype=np.float32)/255.0
H_f,W_f=face_arr.shape[:2]
skin_rgb=face_arr[int(0.15*H_f):int(0.55*H_f),int(0.35*W_f):int(0.65*W_f)].reshape(-1,3).mean(0)
print(f'  skin: rgb=({skin_rgb[0]:.3f},{skin_rgb[1]:.3f},{skin_rgb[2]:.3f})')

def rgb_to_hsv(rgb):
    r,g,b=float(rgb[0]),float(rgb[1]),float(rgb[2])
    maxc=max(r,g,b); delta=maxc-min(r,g,b)
    v=maxc; s=delta/maxc if maxc>0 else 0.0
    if delta==0: h=0.0
    elif maxc==r: h=((g-b)/delta)%6.0/6.0
    elif maxc==g: h=((b-r)/delta+2)/6.0
    else:         h=((r-g)/delta+4)/6.0
    return np.array([h,s,v])

REF_OFFSET=np.array([-0.0066,-0.0213,-0.0380])
skin_hsv=rgb_to_hsv(skin_rgb)
target_hsv=np.clip(skin_hsv+REF_OFFSET,[0,0,0],[1,1,1])
H_tm,W_tm=tmpl.shape[:2]
tg_rgb=tmpl[int(0.05*H_tm):int(0.30*H_tm),int(0.30*W_tm):int(0.70*W_tm),:3].reshape(-1,3).astype(np.float32).mean(0)/255.0
tg_hsv=rgb_to_hsv(tg_rgb)
dh=target_hsv[0]-tg_hsv[0]; ds=target_hsv[1]-tg_hsv[1]; dv=target_hsv[2]-tg_hsv[2]

def shift_hsv_image(img_rgba,dh,ds,dv):
    rgb=img_rgba[:,:,:3].astype(np.float32)/255.0; alpha=img_rgba[:,:,3:4]
    maxc=rgb.max(2,keepdims=True); delta=maxc-rgb.min(2,keepdims=True)
    v=np.clip(maxc+dv,0,1); s=np.clip(np.where(maxc>0,delta/(maxc+1e-10),0.0)+ds,0,1)
    r_=rgb[:,:,0:1]; g_=rgb[:,:,1:2]; b_=rgb[:,:,2:3]; h=np.zeros_like(r_)
    mr=(maxc==r_)&(delta>0); mg=(maxc==g_)&(delta>0)&~mr; mb=~mr&~mg&(delta>0)
    h[mr]=(((g_-b_)/(delta+1e-10))[mr])%6.0/6.0
    h[mg]=(((b_-r_)/(delta+1e-10))[mg]+2)/6.0
    h[mb]=(((r_-g_)/(delta+1e-10))[mb]+4)/6.0
    h=np.clip(h+dh,0,1); i=(h*6).astype(int)%6; f=h*6-np.floor(h*6)
    p=v*(1-s); q=v*(1-f*s); t_=v*(1-(1-f)*s)
    or_=np.where(i==0,v,np.where(i==1,q,np.where(i==2,p,np.where(i==3,p,np.where(i==4,t_,v)))))
    og_=np.where(i==0,t_,np.where(i==1,v,np.where(i==2,v,np.where(i==3,q,np.where(i==4,p,p)))))
    ob_=np.where(i==0,p,np.where(i==1,p,np.where(i==2,t_,np.where(i==3,v,np.where(i==4,v,q)))))
    out_rgb=np.clip(np.concatenate([or_,og_,ob_],2)*255,0,255).astype(np.uint8)
    return np.concatenate([out_rgb,alpha],2)

gens=shift_hsv_image(tmpl,dh,ds,dv)
ta=tip[:,:,3:4].astype(np.float32)/255.0
gens=(gens.astype(np.float32)*(1-ta)+tip.astype(np.float32)*ta).astype(np.uint8)
save_png(gens, os.path.join(tex_dst,'Gen_male.png'))
print('  -> Gen_male.png')

# ── Bundle all Mowang_nixi clothing from source ───────────────────────────────
print('\n=== Bundling Mowang_nixi clothing ===')
with zipfile.ZipFile(SRC_PKG,'r') as z:
    for entry in z.namelist():
        if entry.startswith('Custom/Clothing/Female/Mowang_nixi/') and not entry.endswith('/'):
            data=z.read(entry)
            if entry.endswith(('.vam','.vaj')):
                txt=data.decode('utf-8',errors='replace')
                if 'SELF:/' in txt:
                    txt=txt.replace('SELF:/',f'{P}:/'); data=txt.encode('utf-8')
            dst=os.path.join(STAGE,entry.replace('/',os.sep))
            os.makedirs(os.path.dirname(dst),exist_ok=True)
            with open(dst,'wb') as fh: fh.write(data)
            print(f'  {entry.split("/")[-1]}')

# ── VL_13 Shorts_M: bundle Female/ as-is + copy to Male/ (ClothingMale) ──────
print('\n=== VL_13 Shorts_M → Male/ ===')
VL13_SHORTS=['Shorts_M_Set_Suspenders_pulled','Shorts_M_Set_Suspenders_v2','Shorts_M_Set_v2_pulled']
with zipfile.ZipFile(SRC_PKG,'r') as z:
    for item in VL13_SHORTS:
        for ext in ['.vam','.vab','.vaj','.jpg']:
            src=f'Custom/Clothing/Female/VL_13/Shorts_M/{item}{ext}'
            if src not in z.namelist(): continue
            data=z.read(src)
            # Keep Female/ copy as-is (for storables that ref Female/ path)
            dst_f=os.path.join(STAGE,src.replace('/',os.sep))
            os.makedirs(os.path.dirname(dst_f),exist_ok=True)
            with open(dst_f,'wb') as fh: fh.write(data)
            # Male/ copy: change itemType in .vam
            male_rel=src.replace('Custom/Clothing/Female/','Custom/Clothing/Male/')
            if ext=='.vam':
                d=json.loads(data.decode('utf-8'))
                d['itemType']='ClothingMale'
                data_m=json.dumps(d).encode('utf-8')
            elif ext=='.vaj':
                txt=data.decode('utf-8',errors='replace')
                txt=txt.replace('SELF:/',f'{P}:/'); data_m=txt.encode('utf-8')
            else:
                data_m=data
            dst_m=os.path.join(STAGE,male_rel.replace('/',os.sep))
            os.makedirs(os.path.dirname(dst_m),exist_ok=True)
            with open(dst_m,'wb') as fh: fh.write(data_m)
        print(f'  {item}')
    # Also copy the texture folder
    for entry in z.namelist():
        if entry.startswith('Custom/Clothing/Female/VL_13/Shorts_M/texture/') and not entry.endswith('/'):
            data=z.read(entry)
            # Female/ copy
            dst_f=os.path.join(STAGE,entry.replace('/',os.sep))
            os.makedirs(os.path.dirname(dst_f),exist_ok=True)
            with open(dst_f,'wb') as fh: fh.write(data)
            # Male/ copy
            male_rel=entry.replace('Custom/Clothing/Female/','Custom/Clothing/Male/')
            dst_m=os.path.join(STAGE,male_rel.replace('/',os.sep))
            os.makedirs(os.path.dirname(dst_m),exist_ok=True)
            with open(dst_m,'wb') as fh: fh.write(data)
            print(f'  texture/{entry.split("/")[-1]}')

# ── Extract long10 hair → Male/ ───────────────────────────────────────────────
print('\n=== long10 hair ===')
LONG10_ITEMS=['long 10 base','long 10 alt left','long 10 alt right']
with zipfile.ZipFile(LONG10,'r') as z:
    znames=set(z.namelist())
    for item in LONG10_ITEMS:
        for ext in ['.vam','.vab','.vaj']:
            src=f'Custom/Hair/Female/ddaamm/ddaamm/{item}{ext}'
            if src not in znames: print(f'  MISSING {src}'); continue
            data=z.read(src)
            if ext=='.vam':
                d=json.loads(data.decode('utf-8')); d['itemType']='HairMale'
                data=json.dumps(d).encode('utf-8')
            if ext=='.vaj':
                txt=data.decode('utf-8')
                if 'SELF:/' in txt: txt=txt.replace('SELF:/','ddaamm.hair_long10.4:/'); data=txt.encode('utf-8')
            dst=os.path.join(STAGE,f'Custom/Hair/Male/ddaamm/ddaamm/{item}{ext}'.replace('/',os.sep))
            os.makedirs(os.path.dirname(dst),exist_ok=True)
            with open(dst,'wb') as fh: fh.write(data)
    print(f'  {", ".join(LONG10_ITEMS)}')

# ── long17 scalp SoRa from source → Male/ ────────────────────────────────────
print('\n=== long17 scalp SoRa ===')
with zipfile.ZipFile(SRC_PKG,'r') as z:
    for ext in ['.vam','.vab','.vaj']:
        src=f'Custom/Hair/Female/ddaamm/ddaamm/long17 scalp SoRa{ext}'
        data=z.read(src)
        if ext=='.vam':
            d=json.loads(data.decode('utf-8')); d['itemType']='HairMale'
            data=json.dumps(d).encode('utf-8')
        if ext=='.vaj':
            txt=data.decode('utf-8')
            if 'SELF:/' in txt: txt=txt.replace('SELF:/',f'{P}:/'); data=txt.encode('utf-8')
        dst=os.path.join(STAGE,f'Custom/Hair/Male/ddaamm/ddaamm/long17 scalp SoRa{ext}'.replace('/',os.sep))
        os.makedirs(os.path.dirname(dst),exist_ok=True)
        with open(dst,'wb') as fh: fh.write(data)
    print('  done')

# ── Copy morphs → male/ ───────────────────────────────────────────────────────
print('\n=== Morphs ===')
morph_dst=os.path.join(STAGE,r'Custom\Atom\Person\Morphs\male')
os.makedirs(morph_dst,exist_ok=True)
with zipfile.ZipFile(SRC_PKG,'r') as z:
    for entry in [
        'Custom/Atom/Person/Morphs/female/Leyla - Head.vmb',
        'Custom/Atom/Person/Morphs/female/Leyla - Head.vmi',
        'Custom/Atom/Person/Morphs/female/Leyla L - Body.vmb',
        'Custom/Atom/Person/Morphs/female/Leyla L - Body.vmi',
        'Custom/Atom/Person/Morphs/female/Leyla M - Body.vmb',
        'Custom/Atom/Person/Morphs/female/Leyla M - Body.vmi',
        'Custom/Atom/Person/Morphs/female/Leyla S - Body.vmb',
        'Custom/Atom/Person/Morphs/female/Leyla S - Body.vmi',
    ]:
        data=z.read(entry); fname=os.path.basename(entry)
        if fname.endswith('.vmi'):
            txt=data.decode('utf-8',errors='replace')
            txt=txt.replace('SELF:/Custom/Atom/Person/Morphs/female/',f'{P}:/Custom/Atom/Person/Morphs/male/')
            data=txt.encode('utf-8')
        with open(os.path.join(morph_dst,fname),'wb') as fh: fh.write(data)
    print(f'  Head + L/M/S Body')

# ── Shared constants ──────────────────────────────────────────────────────────
NEW_HAIR=[
    {'id':f'{P}:/Custom/Hair/Male/ddaamm/ddaamm/long 10 base.vam',    'internalId':'ddaamm:long 10 base',    'enabled':'true'},
    {'id':f'{P}:/Custom/Hair/Male/ddaamm/ddaamm/long 10 alt left.vam','internalId':'ddaamm:long 10 alt left','enabled':'true'},
    {'id':f'{P}:/Custom/Hair/Male/ddaamm/ddaamm/long 10 alt right.vam','internalId':'ddaamm:long 10 alt right','enabled':'true'},
    {'id':f'{P}:/Custom/Hair/Male/ddaamm/ddaamm/long17 scalp SoRa.vam','internalId':'ddaamm:long17 scalp SoRa','enabled':'true'},
]
WEBU={'id':'WeebU.Futa_panty_hose_v2.2:/Custom/Clothing/Male/WeebU/Panty hose 1/Panty hose 1.vam',
      'internalId':'WeebU:Panty hose 1','enabled':'true'}
DROP_IDS={'BreastControl','BreastPhysicsMesh','BreastInOut','FemaleAnatomy',
          'BendFix','AutoJawMouthMorph','AutoExpressions'}
SKIP_MORPHS={'Nipples','Labia majora-spread-LLow','Labia majora-spread-RLow',
             'Labia minora-relaxation','Labia minora-size','Labia minora-thickness','Pubic Area Size'}
VL13_MALE_IDS={
    f'{P}:/Custom/Clothing/Male/VL_13/Shorts_M/Shorts_M_Set_Suspenders_pulled.vam',
    f'{P}:/Custom/Clothing/Male/VL_13/Shorts_M/Shorts_M_Set_Suspenders_v2.vam',
    f'{P}:/Custom/Clothing/Male/VL_13/Shorts_M/Shorts_M_Set_v2_pulled.vam',
}

EXTERNAL_REMAP={
    'IAmAFox.Simple_Anklet_Chains.latest:/Custom/Clothing/Female/IAmAFox/Chain R Foot/Chain R Foot.vam':
        f'{P}:/Custom/Clothing/Male/IAmAFox/Chain R Foot/Chain R Foot.vam',
    'IAmAFox.Simple_Anklet_Chains.latest:/Custom/Clothing/Female/IAmAFox/Chain L Foot/Chain L Foot.vam':
        f'{P}:/Custom/Clothing/Male/IAmAFox/Chain L Foot/Chain L Foot.vam',
    'Giallone.Waist_Chain.latest:/Custom/Clothing/Female/giallone/Waist chain/Waist chain.vam':
        f'{P}:/Custom/Clothing/Male/giallone/Waist chain/Waist chain.vam',
    'maru01.flower_lei.latest:/Custom/Clothing/Female/maru01/acc_flower01/acc_flower01.vam':
        f'{P}:/Custom/Clothing/Male/maru01/acc_flower01/acc_flower01.vam',
    'Jackaroo.New_Mouth_Female.latest:/Custom/Clothing/Female/Jackaroo/New Gums and Tongue/New Gums and Tongue.vam':
        f'{P}:/Custom/Clothing/Male/Jackaroo/New Gums and Tongue/New Gums and Tongue.vam',
    'Jackaroo.New_Mouth_Female.latest:/Custom/Clothing/Female/Jackaroo/New Teeth/New Teeth.vam':
        f'{P}:/Custom/Clothing/Male/Jackaroo/New Teeth/New Teeth.vam',
    'Skynet.Fingernails_HD.latest:/Custom/Clothing/Female/Skynet/Fingernails HD shorter/Fingernails HD shorter.vam':
        f'{P}:/Custom/Clothing/Male/Skynet/Fingernails HD shorter/Fingernails HD shorter.vam',
    'Skynet.toenails_HD.latest:/Custom/Clothing/Female/Skynet/Toenails HD shorter/Toenails HD shorter.vam':
        f'{P}:/Custom/Clothing/Male/Skynet/Toenails HD shorter/Toenails HD shorter.vam',
    'xxxa.EyeSDW.latest:/Custom/Clothing/Female/xxxa/EyeSDW/EyeSDW_v3.vam':
        f'{P}:/Custom/Clothing/Male/xxxa/EyeSDW/EyeSDW_v3.vam',
}

def fix_clothing_id(cid):
    """Remap external Female/ IDs to bundled Male/ paths; update SELF:/ and VL_13 refs."""
    if cid in EXTERNAL_REMAP: return EXTERNAL_REMAP[cid]
    cid=cid.replace('SELF:/',f'{P}:/')
    cid=cid.replace(f'{P}:/Custom/Clothing/Female/VL_13/',
                    f'{P}:/Custom/Clothing/Male/VL_13/')
    return cid

def extract_clothing_to_male(pkg_path, female_folder):
    """Copy all files from a Female/ clothing folder to Male/ path in stage, ClothingMale."""
    male_folder=female_folder.replace('Custom/Clothing/Female/','Custom/Clothing/Male/')
    with zipfile.ZipFile(pkg_path) as z:
        for entry in z.namelist():
            if not entry.startswith(female_folder+'/') or entry.endswith('/'): continue
            data=z.read(entry)
            filename=entry[len(female_folder)+1:]
            if entry.endswith('.vam'):
                d=json.loads(data.decode('utf-8')); d['itemType']='ClothingMale'
                data=json.dumps(d).encode('utf-8')
            elif entry.endswith('.vaj'):
                txt=data.decode('utf-8',errors='replace')
                txt=txt.replace('SELF:/Custom/Clothing/Female/',f'{P}:/Custom/Clothing/Male/')
                txt=txt.replace('SELF:/',f'{P}:/'); data=txt.encode('utf-8')
            dst=os.path.join(STAGE,f'{male_folder}/{filename}'.replace('/',os.sep))
            os.makedirs(os.path.dirname(dst),exist_ok=True)
            with open(dst,'wb') as fh: fh.write(data)
            print(f'  {male_folder.split("/")[-1]}/{filename}')

def build_appearance_preset(size, src_storables):
    orig={s['id']:s for s in src_storables}
    body_morph=f'Leyla {size} - Body'

    geo=copy.deepcopy(orig['geometry'])
    geo['character']='Male Custom'; geo['useFemaleMorphsOnMale']='true'
    geo.pop('useMaleMorphsOnFemale',None); geo.pop('useAuxBreastColliders',None)

    # Keep ALL clothing, update SELF:/ and VL_13 paths, add WeebU
    new_cloth=[]
    for c in geo.get('clothing',[]):
        c2=copy.deepcopy(c); c2['id']=fix_clothing_id(c2['id'])
        new_cloth.append(c2)
    new_cloth.append(WEBU)
    # Add all 3 VL_13 Shorts_M variants at Male/ path
    for shorts_name in VL13_SHORTS:
        new_cloth.append({'id':f'{P}:/Custom/Clothing/Male/VL_13/Shorts_M/{shorts_name}.vam',
                          'internalId':f'VL_13:{shorts_name}','enabled':'true'})
    geo['clothing']=new_cloth
    geo['hair']=NEW_HAIR

    new_m=[]
    for m in geo.get('morphs',[]):
        uid=m.get('uid',''); name=m.get('name','')
        if 'female_genitalia' in uid: continue
        if name in SKIP_MORPHS: continue
        m2=copy.deepcopy(m)
        if uid.startswith('SELF:/Custom/Atom/Person/Morphs/female/'):
            m2['uid']=uid.replace('SELF:/Custom/Atom/Person/Morphs/female/',f'{P}:/Custom/Atom/Person/Morphs/male/')
        # Drop body morphs that don't match this size
        if m2.get('name','').startswith('Leyla') and ' - Body' in m2.get('name','') and m2.get('name','')!=body_morph:
            continue
        new_m.append(m2)
    new_m+=[{'uid':'MVR_G2Female','name':'MVR_G2Female','value':'1'},
            {'uid':'Michael 6 Body','name':'Michael 6 Body','value':'0'},
            {'uid':'Michael 6 Head','name':'Michael 6 Head','value':'0'}]
    geo['morphs']=new_m

    tex={
        'id':'textures',
        'faceDiffuseUrl':    f'{P}:/{TEX_DIR}/Face_male.jpg',
        'faceNormalUrl':     f'{P}:/{TEX_DIR}/Face_n_male.jpg',
        'faceGlossUrl':      f'{P}:/{TEX_DIR}/face_G_male.jpg',
        'faceSpecularUrl':   f'{P}:/{TEX_DIR}/Face_s_male.jpg',
        'faceDecalUrl':      '',
        'torsoDiffuseUrl':   f'{P}:/{TEX_DIR}/Torso_male.jpg',
        'torsoNormalUrl':    f'{P}:/{TEX_DIR}/Torso_n_male.jpg',
        'torsoSpecularUrl':  '','torsoGlossUrl':'',
        'torsoDecalUrl':     f'{P}:/{TEX_DIR}/Decal_Tanlines_Torso_male.png',
        'limbsDiffuseUrl':   f'{P}:/{TEX_DIR}/Limbs_male.jpg',
        'limbsNormalUrl':    f'{P}:/{TEX_DIR}/Limbs_n_male.jpg',
        'limbsSpecularUrl':  '','limbsGlossUrl':'',
        'genitalsDiffuseUrl':f'{P}:/{TEX_DIR}/Gen_male.png',
        'genitalsNormalUrl': '','genitalsSpecularUrl':'','genitalsGlossUrl':'','genitalsDecalUrl':'',
        'faceDetailUrl':'','torsoDetailUrl':'','limbsDetailUrl':'','genitalsDetailUrl':'',
    }
    for k,v in orig.get('textures',{}).items():
        if k.startswith('autoBlend'): tex[k]=v

    skin=copy.deepcopy(orig['skin']); skin.pop('Face',None); skin.pop('Nails',None); skin.pop('Pubic Hair',None)

    storables=[geo,tex,skin]
    for sid in ['irises','sclera','lacrimals','FemaleEyelashes','MaleEyelashes',
                'teeth','tongue','mouth','EyelidControl','GluteControl',
                'LowerPhysicsMesh','SoftBodyPhysicsEnabler','rescaleObject']:
        if sid in orig: storables.append(copy.deepcopy(orig[sid]))

    existing={s['id'] for s in storables}
    for s in src_storables:
        if s['id'] in DROP_IDS or s['id'] in existing: continue
        storables.append(copy.deepcopy(s))

    vap_text=json.dumps({'setUnlistedParamsToDefault':'true','storables':storables})
    vap_text=vap_text.replace('SELF:/',f'{P}:/')
    vap_text=vap_text.replace(f'{P}:/Custom/Clothing/Female/VL_13/',f'{P}:/Custom/Clothing/Male/VL_13/')
    return json.loads(vap_text)

def build_clothing_preset(src_vap):
    """Update SELF:/ refs and VL_13 Female→Male paths in clothing presets."""
    vap=copy.deepcopy(src_vap)
    geo=next((s for s in vap['storables'] if s['id']=='geometry'),None)
    if geo:
        new_cloth=[]
        for c in geo.get('clothing',[]):
            c2=copy.deepcopy(c); c2['id']=fix_clothing_id(c2['id'])
            new_cloth.append(c2)
        geo['clothing']=new_cloth
    text=json.dumps(vap)
    text=text.replace('SELF:/',f'{P}:/')
    text=text.replace(f'{P}:/Custom/Clothing/Female/VL_13/',f'{P}:/Custom/Clothing/Male/VL_13/')
    return json.loads(text)

# ── Extract external clothing → Male/ ────────────────────────────────────────
print('\n=== External clothing → Male/ ===')
extract_clothing_to_male(IAIFOX_PKG,  'Custom/Clothing/Female/IAmAFox/Chain R Foot')
extract_clothing_to_male(IAIFOX_PKG,  'Custom/Clothing/Female/IAmAFox/Chain L Foot')
extract_clothing_to_male(GIALLONE_PKG,'Custom/Clothing/Female/giallone/Waist chain')
extract_clothing_to_male(MARU01_PKG,  'Custom/Clothing/Female/maru01/acc_flower01')
extract_clothing_to_male(JACKAROO_PKG,'Custom/Clothing/Female/Jackaroo/New Gums and Tongue')
extract_clothing_to_male(JACKAROO_PKG,'Custom/Clothing/Female/Jackaroo/New Teeth')
extract_clothing_to_male(SKYNETF_PKG, 'Custom/Clothing/Female/Skynet/Fingernails HD shorter')
extract_clothing_to_male(SKYNETT_PKG, 'Custom/Clothing/Female/Skynet/Toenails HD shorter')
extract_clothing_to_male(XXXA_PKG,    'Custom/Clothing/Female/xxxa/EyeSDW')

# ── Build appearance presets ──────────────────────────────────────────────────
print('\n=== Appearance presets ===')
with zipfile.ZipFile(SRC_PKG,'r') as z:
    app_dir=os.path.join(STAGE,r'Custom\Atom\Person\Appearance')
    os.makedirs(app_dir,exist_ok=True)
    for size in ['L','M','S']:
        src_vap=json.loads(z.read(f'Custom/Atom/Person/Appearance/Preset_Leyla {size}.vap'))
        vap=build_appearance_preset(size, src_vap['storables'])
        fname=f'Preset_Leyla_{size}_Male.vap'
        with open(os.path.join(app_dir,fname),'w',encoding='utf-8') as fh: json.dump(vap,fh,indent=3)
        geo=next(s for s in vap['storables'] if s['id']=='geometry')
        print(f'  {fname}: {len(vap["storables"])} storables, {len(geo["clothing"])} clothing, {len(geo["morphs"])} morphs')

# ── Build clothing presets ────────────────────────────────────────────────────
print('\n=== Clothing presets ===')
with zipfile.ZipFile(SRC_PKG,'r') as z:
    cl_dir=os.path.join(STAGE,r'Custom\Atom\Person\Clothing')
    os.makedirs(cl_dir,exist_ok=True)
    cloth_presets=[
        ('Custom/Atom/Person/Clothing/Preset_Leyla.vap',       'Preset_Leyla_Male.vap'),
        ('Custom/Atom/Person/Clothing/Preset_Leyla 2.vap',     'Preset_Leyla_2_Male.vap'),
        ('Custom/Atom/Person/Clothing/Preset_Leyla 4.vap',     'Preset_Leyla_4_Male.vap'),
        ('Custom/Atom/Person/Clothing/Preset_Leyla_cleave.vap','Preset_Leyla_cleave_Male.vap'),
    ]
    for src_path, out_name in cloth_presets:
        if src_path not in z.namelist(): continue
        src_vap=json.loads(z.read(src_path))
        updated=build_clothing_preset(src_vap)
        with open(os.path.join(cl_dir,out_name),'w',encoding='utf-8') as fh: json.dump(updated,fh,indent=3)
        print(f'  {out_name}')
    # Copy preview images
    for src_path,_ in cloth_presets:
        img_path=src_path.replace('.vap','.jpg')
        if img_path in z.namelist():
            fname=os.path.basename(img_path).replace('Preset_Leyla','Preset_Leyla_Male').replace('.jpg','_Male.jpg')
            with open(os.path.join(cl_dir,fname),'wb') as fh: fh.write(z.read(img_path))

# ── meta.json ─────────────────────────────────────────────────────────────────
print('\n=== meta.json ===')
content_list=[]
for root,dirs,files in os.walk(STAGE):
    for fname in files:
        rel=os.path.relpath(os.path.join(root,fname),STAGE).replace(os.sep,'/')
        if rel!='meta.json': content_list.append(rel)
content_list.sort()

meta={
    'licenseType':'CC BY-NC-SA','creatorName':'caelryn',
    'packageName':'LeylaMale','standardReferenceVersionOption':'Latest',
    'version':2,'description':'Leyla L/M/S converted to male. All clothing kept; VL_13 Shorts_M converted to Male path. All accessories bundled at Male/ paths.',
    'credits':'caelryn. Hair by ddaamm.','tags':['male','looks'],
    'promotionalLink':'','programVersion':'1.22.0.3','contentList':content_list,
    'dependencies':{
        'WeebU.Futa_panty_hose_v2.2':           {'licenseType':'CC BY','dependencies':{}},
        'ddaamm.hair_long10.4':                 {'licenseType':'CC BY','dependencies':{}},
        'NorthernShikima.SkinMicroDetail.8':    {'licenseType':'CC BY','dependencies':{}},
        'YameteOuji.Sneaker_Egregious.latest':  {'licenseType':'CC BY','dependencies':{}},
        'YameteOuji.Neck_ChokerLaceA.latest':   {'licenseType':'CC BY','dependencies':{}},
        'EuLinRabei.Legacy_of_Chel.latest':     {'licenseType':'CC BY','dependencies':{}},
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
