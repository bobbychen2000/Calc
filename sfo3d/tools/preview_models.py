import sys, gzip, json, struct, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
def load(path):
    raw = gzip.decompress(open(path,'rb').read())
    assert raw[:4]==b'SFOM'; v,hl = struct.unpack('<II', raw[4:12]); h=json.loads(raw[12:12+hl]); blob=raw[12+hl:]
    nv=h['nv']; q=h['quant']
    pq=np.frombuffer(blob, np.uint16, nv*3, h['offsets']['pos']).reshape(-1,3).astype(np.float64)
    P=pq*np.array(q['pscale'])+np.array(q['pmin'])
    Z=np.frombuffer(blob, np.uint8, nv, h['offsets']['zone'])
    it=np.uint16 if h['idxType']=='u16' else np.uint32
    I=np.frombuffer(blob, it, h['ni'], h['offsets']['idx']).reshape(-1,3)
    return h,P,Z,I
keys=sys.argv[1:]
fig,axs=plt.subplots(len(keys),3,figsize=(18,4*len(keys)))
cols={0:'#999999',1:'#1f4fbf',2:'#d4561c',3:'#111111',4:'#8a2be2',5:'#00b3b3',6:'#e6c200',7:'#6b8e23',8:'#ff00ff'}
for r,k in enumerate(keys):
    h,P,Z,I=load(f'data/models/{k}.sfom')
    for c,(a,b,t) in enumerate([(0,1,'side (x fwd, y up)'),(2,1,'front (z right, y up)'),(0,2,'top (x fwd, z right)')]):
        ax=axs[r][c] if len(keys)>1 else axs[c]
        for zv in np.unique(Z):
            s=Z==zv; ax.scatter(P[s,a],P[s,b],s=0.2,c=cols.get(int(zv),'r'),label=str(zv))
        ax.set_aspect('equal'); ax.set_title(f'{k} {t}'); ax.grid(True,alpha=0.3)
    (axs[r][0] if len(keys)>1 else axs[0]).legend(markerscale=20,fontsize=7,loc='upper right')
plt.tight_layout(); plt.savefig('out/model_preview.png',dpi=70)
