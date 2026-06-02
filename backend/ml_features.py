
"""
ML-Assisted Feature Extraction v1.5.7
CPU-only feature extraction that supports the physical bottle signature engine.
"""
from __future__ import annotations
from typing import Dict, Optional
import math
import cv2
import numpy as np
from runtime_config import max_image_dim
from dl_segmentation import segment_bottle

ML_VECTOR_KEYS = []
for _view in ["front", "side", "top"]:
    for _cluster in [1,2]:
        ML_VECTOR_KEYS += [f"ml_{_view}_kmeans_r{_cluster}", f"ml_{_view}_kmeans_g{_cluster}", f"ml_{_view}_kmeans_b{_cluster}"]
    ML_VECTOR_KEYS += [f"ml_{_view}_orb_keypoint_density", f"ml_{_view}_texture_complexity"]
    ML_VECTOR_KEYS += [f"ml_{_view}_gradient_h{i}" for i in range(8)]
ML_VECTOR_KEYS += ["ml_cross_view_shape_consistency", "ml_cross_view_color_consistency", "ml_capture_quality_score"]

def _load(path: Optional[str]):
    return cv2.imread(path) if path else None

def _resize(img, max_dim=700):
    h,w=img.shape[:2]
    if max(h,w)>max_dim:
        s=max_dim/max(h,w)
        return cv2.resize(img,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    return img

def _mask(img):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    blur=cv2.GaussianBlur(gray,(5,5),0)
    _,a=cv2.threshold(blur,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    _,b=cv2.threshold(blur,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    def score(m):
        cnts,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if not cnts: return -1
        c=max(cnts,key=cv2.contourArea); area=cv2.contourArea(c); x,y,w,h=cv2.boundingRect(c)
        center=1-abs((x+w/2)-img.shape[1]/2)/max(img.shape[1],1)
        return area/max(img.shape[0]*img.shape[1],1)+center
    m=a if score(a)>score(b) else b
    return cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8),iterations=2)

def _kmeans(img, mask, k=3):
    pix=img[mask>0]
    if pix.size<30: pix=img.reshape((-1,3))
    pix=pix.astype(np.float32)
    if len(pix)>7000: pix=pix[np.linspace(0,len(pix)-1,7000).astype(int)]
    if len(pix)<k:
        b,g,r=np.median(pix,axis=0); return np.array([[r,g,b]]*k,dtype=np.float32),0.0
    crit=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,25,0.4)
    comp, labels, centers=cv2.kmeans(pix,k,None,crit,3,cv2.KMEANS_PP_CENTERS)
    counts=np.bincount(labels.flatten(),minlength=k); centers=centers[np.argsort(-counts)]
    return centers[:,[2,1,0]], float(comp/max(len(pix)*255.0*255.0,1))

def _orb_density(img, mask):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    try:
        kp=cv2.ORB_create(nfeatures=300).detect(gray,mask)
    except Exception:
        kp=[]
    area=float(np.sum(mask>0))
    return float(min(len(kp)/max(area/10000.0,1.0)/250.0,1.0))

def _texture(img, mask):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY); lap=cv2.Laplacian(gray,cv2.CV_64F)
    vals=lap[mask>0]
    if vals.size==0: vals=lap.flatten()
    return float(np.clip(np.var(vals)/5000.0,0,1))

def _grad_hist(img, mask):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    gx=cv2.Sobel(gray,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(gray,cv2.CV_32F,0,1,ksize=3)
    mag,ang=cv2.cartToPolar(gx,gy,angleInDegrees=True)
    angles=ang[mask>0]; mags=mag[mask>0]
    if angles.size<20: angles=ang.flatten(); mags=mag.flatten()
    hist,_=np.histogram(angles,bins=8,range=(0,360),weights=mags)
    hist=hist.astype(np.float32); total=float(hist.sum())
    return hist/total if total>0 else hist

def _bbox(mask):
    cnts,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not cnts: return 0.0,0.0
    x,y,w,h=cv2.boundingRect(max(cnts,key=cv2.contourArea)); return float(w),float(h)

def _view(path, name):
    img=_load(path)
    if img is None: return {}
    img=_resize(img); mask=_mask(img); colors,comp=_kmeans(img,mask)
    hist=_grad_hist(img,mask); w,h=_bbox(mask)
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    brightness=float(np.mean(gray)/255.0); contrast=float(np.std(gray)/128.0); fill=float(np.mean(mask>0))
    q=float(np.clip(contrast*0.35+fill*0.45+(1-abs(brightness-0.5)*2)*0.20,0,1))
    out={}
    for i in range(2):
        r,g,b=colors[i]
        out[f'ml_{name}_kmeans_r{i+1}']=float(r); out[f'ml_{name}_kmeans_g{i+1}']=float(g); out[f'ml_{name}_kmeans_b{i+1}']=float(b)
    out[f'ml_{name}_color_cluster_compactness']=float(comp)
    out[f'ml_{name}_orb_keypoint_density']=_orb_density(img,mask)
    out[f'ml_{name}_texture_complexity']=_texture(img,mask)
    for i,v in enumerate(hist): out[f'ml_{name}_gradient_h{i}']=float(v)
    out[f'ml_{name}_bbox_w']=w; out[f'ml_{name}_bbox_h']=h; out[f'ml_{name}_bbox_aspect']=float(h/max(w,1))
    out[f'ml_{name}_quality']=q
    return out

def extract_ml_features(front_path, side_path, top_path) -> Dict[str,float]:
    out={}; out.update(_view(front_path,'front')); out.update(_view(side_path,'side')); out.update(_view(top_path,'top'))
    aspects=[out.get(f'ml_{v}_bbox_aspect') for v in ['front','side','top'] if out.get(f'ml_{v}_bbox_aspect')]
    out['ml_cross_view_shape_consistency']=float(1-np.clip(np.std(aspects)/max(np.mean(aspects),1e-6),0,1)) if len(aspects)>=2 else 0.0
    colors=[]
    for v in ['front','side','top']:
        if out.get(f'ml_{v}_kmeans_r1') is not None:
            colors.append([out[f'ml_{v}_kmeans_r1'],out[f'ml_{v}_kmeans_g1'],out[f'ml_{v}_kmeans_b1']])
    if len(colors)>=2:
        arr=np.array(colors,dtype=np.float32); mean=arr.mean(axis=0); dist=np.linalg.norm(arr-mean,axis=1)
        out['ml_cross_view_color_consistency']=float(1-np.clip(np.mean(dist)/255.0,0,1))
    else: out['ml_cross_view_color_consistency']=0.0
    qs=[out.get(f'ml_{v}_quality') for v in ['front','side','top'] if out.get(f'ml_{v}_quality') is not None]
    out['ml_capture_quality_score']=float(np.mean(qs)) if qs else 0.0
    out['ml_assisted_enabled']=1.0
    return {k:float(v) for k,v in out.items() if isinstance(v,(int,float)) and not math.isnan(float(v))}

def _vector(sig):
    vals=[]
    for k in ML_VECTOR_KEYS:
        v=float(sig.get(k,0.0))
        if 'kmeans_' in k and any(c in k for c in ['_r','_g','_b']): v/=255.0
        vals.append(v)
    return np.array(vals,dtype=np.float32)

def cosine_similarity_from_signatures(a,b):
    va=_vector(a); vb=_vector(b); denom=float(np.linalg.norm(va)*np.linalg.norm(vb))
    return 0.0 if denom<=1e-9 else float(np.clip(np.dot(va,vb)/denom,0,1))

def euclidean_similarity_from_signatures(a,b):
    va=_vector(a); vb=_vector(b); dist=float(np.linalg.norm(va-vb)/max(len(ML_VECTOR_KEYS)**0.5,1))
    return float(np.clip(1-dist,0,1))
