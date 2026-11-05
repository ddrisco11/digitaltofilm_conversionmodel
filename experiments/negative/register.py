from pathlib import Path
import cv2,numpy as np,json
from PIL import Image
cv2.setRNGSeed(83)
def contrast(rgb):
 x=np.mean(rgb,axis=2);low,high=np.percentile(x,[1,99])
 return cv2.createCLAHE(2,(5,5)).apply(np.uint8(255*np.clip((x-low)/(high-low),0,1)))
def register(a,p):
 d=-np.log10(np.maximum(a,1/65535))
 # Match texture after neutralizing per-channel ranges.
 lo,hi=np.percentile(d,[2,98],axis=(0,1));ref=contrast((d-lo)/(hi-lo))
 src=contrast(p);sift=cv2.SIFT_create(contrastThreshold=.012)
 k1,f1=sift.detectAndCompute(src,None);k2,f2=sift.detectAndCompute(ref,None)
 matches=cv2.BFMatcher().knnMatch(f1,f2,k=2)
 good=[v for v,w in matches if v.distance<.80*w.distance]
 s=np.float32([k1[v.queryIdx].pt for v in good]);t=np.float32([k2[v.trainIdx].pt for v in good])
 M,inliers=cv2.findHomography(s,t,cv2.RANSAC,2.5);n=int(inliers.sum())
 if n<10:raise ValueError(f'Only {n} inliers')
 h,w=a.shape[:2]; pp=cv2.warpPerspective(p,M,(w,h));mask=cv2.warpPerspective(np.full(p.shape[:2],255,np.uint8),M,(w,h))
 mask=cv2.erode(mask,np.ones((9,9),np.uint8)); mask[:6]=mask[-6:]=mask[:,:6]=mask[:,-6:]=0
 assert (mask>250).mean()>.5
 return pp,mask>250,n
if __name__=='__main__':
 for r in json.load(open(Path(__file__).with_name('manifest.json')))['rows']:
  name=r['id'];a=np.load(name+'.npy')/65535.;p=np.asarray(Image.open(name+'.jpg').convert('RGB'))/255.
  pp,mask,n=register(a,p)
  np.savez('aligned-'+name+'.npz',negative=a.astype('f4'),positive=pp.astype('f4'),mask=mask)
  print(name,n,round(mask.mean(),3))
