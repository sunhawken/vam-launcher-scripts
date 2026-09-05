"""
build_bezuzu.py — IAmAFox.Bezuzu_Full.1 → IAmAFox.BezuzuMale.1.var
Two appearance presets (Full + Nude). All clothing bundled at Male/ paths.
"""
import zipfile, json, os, copy, shutil
import numpy as np
from PIL import Image
from io import BytesIO
from scipy.ndimage import distance_transform_edt, map_coordinates

SRC_PKG     = r'T:\New folder\AddonPackages\superlady-md\IAmAFox.Bezuzu_Full.1.DISABLED'
RIDDLER_PKG = r'T:\New folder\AddonPackages\resources\Riddler.Skin_9_4k.3.DISABLED'
UVSWAPPER   = r'T:\New folder\AddonPackages\keep\mrmr32.UVSwapper.5.var'
UVDATA      = r'C:\tmp\UVData.json'
NOCTHIS_PKG = r'T:\New folder\AddonPackages\superlady-md\Noc_This.Yor_Hair.1.DISABLED'
PTTAIL_PKG  = r'T:\New folder\AddonPackages\resources\PL_Artists.P_TTail.1.DISABLED'
BOOMON_PIERCE_PKG = r'T:\New folder\AddonPackages\keep\BooMoon.Piercing_pack.1.var'
VAMDOLL_PKG = r'T:\New folder\AddonPackages\resources\VAMDoll.Sweatshirt_v1.1.DISABLED'
BOOMON_PIERCING_PKG = r'T:\New folder\AddonPackages\resources\BooMoon.Piercings.2.DISABLED'
PALEDRIVER_PKG = r'T:\New folder\AddonPackages\resources\paledriver.Eyes_reflection_and_shadow.1.DISABLED'
VIRTA_PKG   = r'T:\New folder\AddonPackages\resources\VirtaArtieMitchel.Ice_Hero_Cosplay_Set.1.DISABLED'
IAMAFOX_CHOKER_PKG = r'T:\New folder\AddonPackages\resources\IAmAFox.Feet_Chokers.1.DISABLED'
OOMPHY_PKG  = r'T:\New folder\AddonPackages\resources\oomphy.kawaii_tatto_pack.1.DISABLED'
VAMLOOKS_PKG= r'T:\New folder\AddonPackages\resources\VamLooks69.Arms_Tattoo.2.DISABLED'
STAGE       = r'C:\tmp\bezuzu_male_v1'
OUT_VAR     = r'T:\New folder\AddonPackages\keep\IAmAFox.BezuzuMale.1.var'
PKG_NAME    = 'IAmAFox.BezuzuMale.1'
TEX_DIR     = 'Custom/Atom/Person/Textures/Bezuzu'
P           = PKG_NAME

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
face_path=os.path.join(tex_dst,'FaceD_male.jpg')
if os.path.exists(face_path) and os.path.exists(os.path.join(tex_dst,'LimbsD_male.jpg')):
    print('Textures already converted, skipping.')
else:
    def load_riddler(zf, fname):
        return np.array(Image.open(BytesIO(zf.read(f'Custom/Atom/Person/Textures/Riddler/Skin 9 4k/{fname}'))).convert('RGBA'))

    with zipfile.ZipFile(RIDDLER_PKG,'r') as zr:
        W4,H4=4096,4096

        print('\n=== Face UV 4K ===')
        r=regions['face']
        mx_f,my_f=build_map(r['male'],r['female'],r['mesh'],W4,H4)
        save_jpg(apply_map(load_riddler(zr,'FaceD.jpg'),mx_f,my_f), face_path)
        save_jpg(apply_map(load_riddler(zr,'FaceN.jpg'),mx_f,my_f), os.path.join(tex_dst,'FaceN_male.jpg'))
        save_jpg(apply_map(load_riddler(zr,'FaceS.jpg'),mx_f,my_f), os.path.join(tex_dst,'FaceS_male.jpg'))
        save_jpg(apply_map(load_riddler(zr,'FaceG.jpg'),mx_f,my_f), os.path.join(tex_dst,'FaceG_male.jpg'))
        # Face decal (Pink.png) — must UV-convert per memory note
        decal_raw=np.array(Image.open(BytesIO(zr.read('Custom/Atom/Person/Textures/Riddler/Skin 9 4k/Decals/Pink.png'))).convert('RGBA'))
        if decal_raw.shape[:2]!=(H4,W4):
            decal_raw=np.array(Image.fromarray(decal_raw).resize((W4,H4),Image.LANCZOS))
        save_png(apply_map(decal_raw,mx_f,my_f), os.path.join(tex_dst,'FaceDecal_Pink_male.png'))
        del mx_f,my_f

        print('\n=== Torso UV 4K ===')
        r=regions['torso']
        mx_t,my_t=build_map(r['male'],r['female'],r['mesh'],W4,H4)
        save_jpg(apply_map(load_riddler(zr,'TorsoD.jpg'),mx_t,my_t), os.path.join(tex_dst,'TorsoD_male.jpg'))
        save_jpg(apply_map(load_riddler(zr,'TorsoN.jpg'),mx_t,my_t), os.path.join(tex_dst,'TorsoN_male.jpg'))
        save_jpg(apply_map(load_riddler(zr,'TorsoS.jpg'),mx_t,my_t), os.path.join(tex_dst,'TorsoS_male.jpg'))
        save_jpg(apply_map(load_riddler(zr,'TorsoG.jpg'),mx_t,my_t), os.path.join(tex_dst,'TorsoG_male.jpg'))
        # Torso decal from oomphy
        with zipfile.ZipFile(OOMPHY_PKG) as zo:
            try:
                td=np.array(Image.open(BytesIO(zo.read('Custom/Atom/Person/Textures/torso/pastel pink heart.png'))).convert('RGBA'))
                if td.shape[:2]!=(H4,W4): td=np.array(Image.fromarray(td).resize((W4,H4),Image.LANCZOS))
                save_png(apply_map(td,mx_t,my_t), os.path.join(tex_dst,'TorsoDecal_male.png'))
            except Exception as e:
                print(f'  torso decal skip: {e}')
        del mx_t,my_t

        print('\n=== Limbs UV 4K ===')
        r=regions['limbs']
        mx_l,my_l=build_map(r['male'],r['female'],r['mesh'],W4,H4)
        save_jpg(apply_map(load_riddler(zr,'LimbsD.jpg'),mx_l,my_l), os.path.join(tex_dst,'LimbsD_male.jpg'))
        save_jpg(apply_map(load_riddler(zr,'LimbsN.jpg'),mx_l,my_l), os.path.join(tex_dst,'LimbsN_male.jpg'))
        save_jpg(apply_map(load_riddler(zr,'LimbsS.jpg'),mx_l,my_l), os.path.join(tex_dst,'LimbsS_male.jpg'))
        save_jpg(apply_map(load_riddler(zr,'LimbsG.jpg'),mx_l,my_l), os.path.join(tex_dst,'LimbsG_male.jpg'))
        # Limbs decal from VamLooks69
        with zipfile.ZipFile(VAMLOOKS_PKG) as vl:
            try:
                ld=np.array(Image.open(BytesIO(vl.read('Custom/Atom/Person/Textures/Arms tattoo.png'))).convert('RGBA'))
                if ld.shape[:2]!=(H4,W4): ld=np.array(Image.fromarray(ld).resize((W4,H4),Image.LANCZOS))
                save_png(apply_map(ld,mx_l,my_l), os.path.join(tex_dst,'LimbsDecal_male.png'))
            except Exception as e:
                print(f'  limbs decal skip: {e}')
        del mx_l,my_l

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

# ── Morphs ────────────────────────────────────────────────────────────────────
print('\n=== Morphs ===')
morph_dst=os.path.join(STAGE,r'Custom\Atom\Person\Morphs\male')
os.makedirs(morph_dst,exist_ok=True)
with zipfile.ZipFile(SRC_PKG,'r') as z:
    for entry in ['Custom/Atom/Person/Morphs/female/Bezuzu - Body.vmb',
                  'Custom/Atom/Person/Morphs/female/Bezuzu - Body.vmi',
                  'Custom/Atom/Person/Morphs/female/Bezuzu - Head.vmb',
                  'Custom/Atom/Person/Morphs/female/Bezuzu - Head.vmi']:
        data=z.read(entry); fname=os.path.basename(entry)
        if fname.endswith('.vmi'):
            txt=data.decode('utf-8',errors='replace')
            txt=txt.replace('SELF:/Custom/Atom/Person/Morphs/female/',f'{P}:/Custom/Atom/Person/Morphs/male/')
            data=txt.encode('utf-8')
        with open(os.path.join(morph_dst,fname),'wb') as fh: fh.write(data)
print('  Head + Body (Genital dropped)')

# ── Extract hair → Male/ ──────────────────────────────────────────────────────
def extract_hair_to_male(pkg_path, female_folder):
    male_folder=female_folder.replace('Custom/Hair/Female/','Custom/Hair/Male/')
    with zipfile.ZipFile(pkg_path) as z:
        for entry in z.namelist():
            if not entry.startswith(female_folder+'/') or entry.endswith('/'): continue
            data=z.read(entry)
            filename=entry[len(female_folder)+1:]
            if entry.endswith('.vam'):
                d=json.loads(data.decode('utf-8')); d['itemType']='HairMale'
                data=json.dumps(d).encode('utf-8')
            elif entry.endswith('.vaj'):
                txt=data.decode('utf-8',errors='replace')
                txt=txt.replace('SELF:/Custom/Hair/Female/',f'{P}:/Custom/Hair/Male/')
                txt=txt.replace('SELF:/',f'{P}:/'); data=txt.encode('utf-8')
            dst=os.path.join(STAGE,f'{male_folder}/{filename}'.replace('/',os.sep))
            os.makedirs(os.path.dirname(dst),exist_ok=True)
            with open(dst,'wb') as fh: fh.write(data)
    print(f'  {male_folder.split("/")[-1]}')

print('\n=== Hair → Male/ ===')
extract_hair_to_male(NOCTHIS_PKG,  'Custom/Hair/Female/Noc_this/NT_Yor_Bang2')
extract_hair_to_male(PTTAIL_PKG,   'Custom/Hair/Female/PL_Artists/TwinTailAdd')
extract_hair_to_male(PTTAIL_PKG,   'Custom/Hair/Female/PL_Artists/TwinTailBase1')

# ── Extract clothing → Male/ ──────────────────────────────────────────────────
def extract_clothing_to_male(pkg_path, female_folder):
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
    print(f'  {male_folder.split("/")[-1]}')

def extract_clothing_male_direct(pkg_path, male_folder):
    """Copy an already-Male/ folder directly."""
    with zipfile.ZipFile(pkg_path) as z:
        for entry in z.namelist():
            if not entry.startswith(male_folder+'/') or entry.endswith('/'): continue
            data=z.read(entry)
            filename=entry[len(male_folder)+1:]
            dst=os.path.join(STAGE,f'{male_folder}/{filename}'.replace('/',os.sep))
            os.makedirs(os.path.dirname(dst),exist_ok=True)
            with open(dst,'wb') as fh: fh.write(data)
    print(f'  {male_folder.split("/")[-1]} (pre-built Male/)')

print('\n=== Clothing → Male/ ===')
extract_clothing_to_male(BOOMON_PIERCE_PKG,   'Custom/Clothing/Female/BooMoon/Belly Piercing Basic 3')
extract_clothing_to_male(VAMDOLL_PKG,          'Custom/Clothing/Female/VAMDoll/Sweatshirt')
extract_clothing_to_male(BOOMON_PIERCING_PKG,  'Custom/Clothing/Female/BooMoon/Eyebrow Piercing')
extract_clothing_to_male(VIRTA_PKG,            'Custom/Clothing/Female/VirtaArtieMitchel/ice_hero_bottoms')
extract_clothing_to_male(VIRTA_PKG,            'Custom/Clothing/Female/VirtaArtieMitchel/ice_hero_neck')
extract_clothing_to_male(IAMAFOX_CHOKER_PKG,   'Custom/Clothing/Female/IAmAFox/L Leg Choker')
# paledriver already ships Male/ versions
extract_clothing_male_direct(PALEDRIVER_PKG, 'Custom/Clothing/Male/paledriver/Eyes reflection and shadow')

# ── Constants ─────────────────────────────────────────────────────────────────
NEW_HAIR=[
    {'id':f'{P}:/Custom/Hair/Male/Noc_this/NT_Yor_Bang2/NT_Yor_Bang2.vam',     'internalId':'Noc_This:NT_Yor_Bang2',   'enabled':'true'},
    {'id':f'{P}:/Custom/Hair/Male/PL_Artists/TwinTailAdd/TwinTailAdd.vam',     'internalId':'PL_Artists:TwinTailAdd',  'enabled':'true'},
    {'id':f'{P}:/Custom/Hair/Male/PL_Artists/TwinTailBase1/TwinTailBase1.vam', 'internalId':'PL_Artists:TwinTailBase1','enabled':'true'},
    {'id':'SimV2 Hair','internalId':'SimV2 Hair','enabled':'true'},
]
WEBU={'id':'WeebU.Futa_panty_hose_v2.2:/Custom/Clothing/Male/WeebU/Panty hose 1/Panty hose 1.vam',
      'internalId':'WeebU:Panty hose 1','enabled':'true'}

EXTERNAL_REMAP={
    'BooMoon.Piercing_pack.latest:/Custom/Clothing/Female/BooMoon/Belly Piercing Basic 3/Belly Piercing Basic 3.vam':
        f'{P}:/Custom/Clothing/Male/BooMoon/Belly Piercing Basic 3/Belly Piercing Basic 3.vam',
    'VAMDoll.Sweatshirt_v1.latest:/Custom/Clothing/Female/VAMDoll/Sweatshirt/Sweatshirt.vam':
        f'{P}:/Custom/Clothing/Male/VAMDoll/Sweatshirt/Sweatshirt.vam',
    'BooMoon.Piercings.latest:/Custom/Clothing/Female/BooMoon/Eyebrow Piercing/Eyebrow Piercing.vam':
        f'{P}:/Custom/Clothing/Male/BooMoon/Eyebrow Piercing/Eyebrow Piercing.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes upper shadow.vam':
        f'{P}:/Custom/Clothing/Male/paledriver/Eyes reflection and shadow/Eyes upper shadow.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes bottom shadow.vam':
        f'{P}:/Custom/Clothing/Male/paledriver/Eyes reflection and shadow/Eyes bottom shadow.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes reflection.vam':
        f'{P}:/Custom/Clothing/Male/paledriver/Eyes reflection and shadow/Eyes reflection.vam',
    'VirtaArtieMitchel.Ice_Hero_Cosplay_Set.latest:/Custom/Clothing/Female/VirtaArtieMitchel/ice_hero_bottoms/ice_hero_bottoms.vam':
        f'{P}:/Custom/Clothing/Male/VirtaArtieMitchel/ice_hero_bottoms/ice_hero_bottoms.vam',
    'VirtaArtieMitchel.Ice_Hero_Cosplay_Set.latest:/Custom/Clothing/Female/VirtaArtieMitchel/ice_hero_neck/ice_hero_neck.vam':
        f'{P}:/Custom/Clothing/Male/VirtaArtieMitchel/ice_hero_neck/ice_hero_neck.vam',
    'IAmAFox.Feet_Chokers.latest:/Custom/Clothing/Female/IAmAFox/L Leg Choker/L Leg Choker.vam':
        f'{P}:/Custom/Clothing/Male/IAmAFox/L Leg Choker/L Leg Choker.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes side shadow.vam':
        f'{P}:/Custom/Clothing/Male/paledriver/Eyes reflection and shadow/Eyes side shadow.vam',
}

DROP_IDS={'BreastControl','BreastPhysicsMesh','BreastInOut','FemaleAnatomy',
          'BendFix','AutoJawMouthMorph','AutoExpressions'}
SKIP_MORPHS={'Nipples','Labia majora-spread-LLow','Labia majora-spread-RLow',
             'Labia minora-relaxation','Labia minora-size','Labia minora-thickness','Pubic Area Size'}

def fix_clothing_id(cid):
    if cid in EXTERNAL_REMAP: return EXTERNAL_REMAP[cid]
    return cid.replace('SELF:/',f'{P}:/')

def torso_decal_path():
    p=os.path.join(tex_dst,'TorsoDecal_male.png')
    return f'{P}:/{TEX_DIR}/TorsoDecal_male.png' if os.path.exists(p) else ''

def limbs_decal_path():
    p=os.path.join(tex_dst,'LimbsDecal_male.png')
    return f'{P}:/{TEX_DIR}/LimbsDecal_male.png' if os.path.exists(p) else ''

def build_appearance_preset(src_vap, clothing_ids):
    """Build a male appearance preset from a source VAP and explicit clothing list."""
    orig={s['id']:s for s in src_vap['storables']}

    geo=copy.deepcopy(orig['geometry'])
    geo['character']='Male Custom'; geo['useFemaleMorphsOnMale']='true'
    geo.pop('useMaleMorphsOnFemale',None); geo.pop('useAuxBreastColliders',None)

    geo['hair']=NEW_HAIR

    new_cloth=[fix_clothing_id(cid) for cid in clothing_ids]
    cloth_entries=[]; covered=set()
    for c in geo.get('clothing',[]):
        orig_id=c.get('id','')
        new_id=fix_clothing_id(orig_id)
        if new_id in new_cloth:
            c2=copy.deepcopy(c); c2['id']=new_id; cloth_entries.append(c2); covered.add(new_id)
    for new_id in new_cloth:
        if new_id not in covered:
            name=new_id.split('/')[-1].replace('.vam','')
            cloth_entries.append({'id':new_id,'internalId':name,'enabled':'true'})
    cloth_entries.append(WEBU)
    geo['clothing']=cloth_entries

    new_m=[]
    for m in geo.get('morphs',[]):
        uid=m.get('uid',''); name=m.get('name','')
        if 'female_genitalia' in uid: continue
        if name in SKIP_MORPHS: continue
        m2=copy.deepcopy(m)
        if uid.startswith('SELF:/Custom/Atom/Person/Morphs/female/'):
            m2['uid']=uid.replace('SELF:/Custom/Atom/Person/Morphs/female/',f'{P}:/Custom/Atom/Person/Morphs/male/')
        new_m.append(m2)
    new_m+=[{'uid':'MVR_G2Female','name':'MVR_G2Female','value':'1'},
            {'uid':'Michael 6 Body','name':'Michael 6 Body','value':'0'},
            {'uid':'Michael 6 Head','name':'Michael 6 Head','value':'0'}]
    geo['morphs']=new_m

    tex={
        'id':'textures',
        'faceDiffuseUrl':    f'{P}:/{TEX_DIR}/FaceD_male.jpg',
        'faceNormalUrl':     f'{P}:/{TEX_DIR}/FaceN_male.jpg',
        'faceSpecularUrl':   f'{P}:/{TEX_DIR}/FaceS_male.jpg',
        'faceGlossUrl':      f'{P}:/{TEX_DIR}/FaceG_male.jpg',
        'faceDecalUrl':      f'{P}:/{TEX_DIR}/FaceDecal_Pink_male.png',
        'torsoDiffuseUrl':   f'{P}:/{TEX_DIR}/TorsoD_male.jpg',
        'torsoNormalUrl':    f'{P}:/{TEX_DIR}/TorsoN_male.jpg',
        'torsoSpecularUrl':  f'{P}:/{TEX_DIR}/TorsoS_male.jpg',
        'torsoGlossUrl':     f'{P}:/{TEX_DIR}/TorsoG_male.jpg',
        'torsoDecalUrl':     torso_decal_path(),
        'limbsDiffuseUrl':   f'{P}:/{TEX_DIR}/LimbsD_male.jpg',
        'limbsNormalUrl':    f'{P}:/{TEX_DIR}/LimbsN_male.jpg',
        'limbsSpecularUrl':  f'{P}:/{TEX_DIR}/LimbsS_male.jpg',
        'limbsGlossUrl':     f'{P}:/{TEX_DIR}/LimbsG_male.jpg',
        'limbsDecalUrl':     limbs_decal_path(),
        'genitalsDiffuseUrl':f'{P}:/{TEX_DIR}/Gen_male.png',
        'genitalsNormalUrl':'','genitalsSpecularUrl':'','genitalsGlossUrl':'','genitalsDecalUrl':'',
        'faceDetailUrl':'','torsoDetailUrl':'','limbsDetailUrl':'','genitalsDetailUrl':'',
    }
    orig_tex=orig.get('textures',{})
    for k,v in orig_tex.items():
        if k.startswith('autoBlend'): tex[k]=v

    skin=copy.deepcopy(orig['skin']); skin.pop('Face',None); skin.pop('Nails',None); skin.pop('Pubic Hair',None)

    storables=[geo,tex,skin]
    for sid in ['irises','sclera','lacrimals','FemaleEyelashes','MaleEyelashes',
                'teeth','tongue','mouth','EyelidControl','GluteControl',
                'LowerPhysicsMesh','SoftBodyPhysicsEnabler','rescaleObject']:
        if sid in orig: storables.append(copy.deepcopy(orig[sid]))

    existing={s['id'] for s in storables}
    for s in src_vap['storables']:
        if s['id'] in DROP_IDS or s['id'] in existing: continue
        storables.append(copy.deepcopy(s))

    vap_text=json.dumps({'setUnlistedParamsToDefault':'true','storables':storables})
    vap_text=vap_text.replace('SELF:/',f'{P}:/')
    return json.loads(vap_text)

# ── Build presets ─────────────────────────────────────────────────────────────
print('\n=== Appearance presets ===')
app_dir=os.path.join(STAGE,r'Custom\Atom\Person\Appearance\Bezuzu')
os.makedirs(app_dir,exist_ok=True)

with zipfile.ZipFile(SRC_PKG,'r') as z:
    src_full=json.loads(z.read('Custom/Atom/Person/Appearance/Bezuzu/Preset_Bezuzu Full.vap'))
    src_nude=json.loads(z.read('Custom/Atom/Person/Appearance/Bezuzu/Preset_Bezuzu Nude.vap'))

# Full preset clothing
FULL_CLOTH_IDS=[
    'BooMoon.Piercing_pack.latest:/Custom/Clothing/Female/BooMoon/Belly Piercing Basic 3/Belly Piercing Basic 3.vam',
    'VAMDoll.Sweatshirt_v1.latest:/Custom/Clothing/Female/VAMDoll/Sweatshirt/Sweatshirt.vam',
    'BooMoon.Piercings.latest:/Custom/Clothing/Female/BooMoon/Eyebrow Piercing/Eyebrow Piercing.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes upper shadow.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes bottom shadow.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes reflection.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes side shadow.vam',
    'VirtaArtieMitchel.Ice_Hero_Cosplay_Set.latest:/Custom/Clothing/Female/VirtaArtieMitchel/ice_hero_bottoms/ice_hero_bottoms.vam',
    'VirtaArtieMitchel.Ice_Hero_Cosplay_Set.latest:/Custom/Clothing/Female/VirtaArtieMitchel/ice_hero_neck/ice_hero_neck.vam',
    'IAmAFox.Feet_Chokers.latest:/Custom/Clothing/Female/IAmAFox/L Leg Choker/L Leg Choker.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes side shadow.vam',
]
NUDE_CLOTH_IDS=[
    'BooMoon.Piercing_pack.latest:/Custom/Clothing/Female/BooMoon/Belly Piercing Basic 3/Belly Piercing Basic 3.vam',
    'BooMoon.Piercings.latest:/Custom/Clothing/Female/BooMoon/Eyebrow Piercing/Eyebrow Piercing.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes upper shadow.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes bottom shadow.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes reflection.vam',
    'paledriver.Eyes_reflection_and_shadow.latest:/Custom/Clothing/Female/paledriver/Eyes reflection and shadow/Eyes side shadow.vam',
]

vap_full=build_appearance_preset(src_full, FULL_CLOTH_IDS)
with open(os.path.join(app_dir,'Preset_Bezuzu_Full_Male.vap'),'w',encoding='utf-8') as fh: json.dump(vap_full,fh,indent=3)
geo_f=next(s for s in vap_full['storables'] if s['id']=='geometry')
print(f'  Full: {len(vap_full["storables"])} storables, {len(geo_f["clothing"])} clothing')

vap_nude=build_appearance_preset(src_nude, NUDE_CLOTH_IDS)
with open(os.path.join(app_dir,'Preset_Bezuzu_Nude_Male.vap'),'w',encoding='utf-8') as fh: json.dump(vap_nude,fh,indent=3)
geo_n=next(s for s in vap_nude['storables'] if s['id']=='geometry')
print(f'  Nude: {len(vap_nude["storables"])} storables, {len(geo_n["clothing"])} clothing')

# ── meta.json ─────────────────────────────────────────────────────────────────
print('\n=== meta.json ===')
content_list=[]
for root,dirs,files in os.walk(STAGE):
    for fname in files:
        rel=os.path.relpath(os.path.join(root,fname),STAGE).replace(os.sep,'/')
        if rel!='meta.json': content_list.append(rel)
content_list.sort()

meta={
    'licenseType':'CC BY-NC-SA','creatorName':'IAmAFox',
    'packageName':'BezuzuMale','standardReferenceVersionOption':'Latest',
    'version':1,'description':'Bezuzu converted to male. Textures UV-remapped. All clothing bundled at Male/ paths.',
    'credits':'IAmAFox. Skin by Riddler.','tags':['male','looks'],
    'promotionalLink':'','programVersion':'1.22.0.3','contentList':content_list,
    'dependencies':{
        'WeebU.Futa_panty_hose_v2.2':           {'licenseType':'CC BY','dependencies':{}},
        'mrmr32.UVSwapper.5':                   {'licenseType':'CC BY','dependencies':{}},
        'VAMJFD.FullMouthTexturePack.latest':   {'licenseType':'CC BY','dependencies':{}},
        'TiSeb.Colortone.latest':               {'licenseType':'CC BY','dependencies':{}},
        'MonsterShinkai.LightRigs.latest':      {'licenseType':'CC BY','dependencies':{}},
        'ceq3.MorphMergeAndSplit.2':            {'licenseType':'CC BY','dependencies':{}},
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
