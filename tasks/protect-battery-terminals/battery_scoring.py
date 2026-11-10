"""Geometric battery-storage scoring, with a trial-long safety latch."""
from pathlib import Path
import itertools
import numpy as np
import build_assets as assets
import layout

EPS = .0002
ENGAGEMENT_CONTACT_EPS = .0005
TOP = .7475
TRAY_XY = np.array(layout.TRAY_XY)
TRAY_DATA = np.load(Path(__file__).with_name('library_tray.npz'))
FLOOR = TOP + float(TRAY_DATA['floor_height'])
RIM = TOP + float(TRAY_DATA['rim_height'])
NAMES = [f'battery{i}' for i in range(3)] + [f'cap{i}' for i in range(3)] + ['storage_tray']

def rotation(o):
 q=np.asarray(o.quat_xyzw,dtype=float);q=q/np.linalg.norm(q)
 x,y,z,w=q
 return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                  [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                  [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def world(o,points):return points@rotation(o).T+o.pos

def box(lo,hi):return np.array(list(itertools.product(*zip(lo,hi))))

def planes(outline):
 edges=np.roll(outline,-1,axis=0)-outline
 normals=np.c_[edges[:,1],-edges[:,0]]
 normals/=np.linalg.norm(normals,axis=1)[:,None]
 return normals,np.sum(normals*outline,axis=1),edges

RIM_N,RIM_B,RIM_E=planes(TRAY_DATA['rim'])
BORE_N,BORE_B,_=planes(assets.outline(.066,.040,.003))
CAVITY_N=np.vstack([np.c_[BORE_N,np.zeros(len(BORE_N))],[[0,0,1],[0,0,-1]]])
CAVITY_B=np.r_[BORE_B,.018,0.]
PEDESTAL_SECTION=np.c_[assets.outline(.060,.034,.003),np.full(20,.066)]
MOUTH=np.c_[assets.outline(.068,.042,.004),np.zeros(20)]
BASE=box((-.05,-.0275,0),(.05,.0275,0))

# Exact authored polygonal envelopes, including grip ribs and raised markings.
if not hasattr(assets,'BATTERY_MESHES'):assets.make()
BATTERY_POINTS=np.unique(np.vstack([m.v for m in assets.BATTERY_MESHES]),axis=0)
CAP_POINTS=np.unique(np.vstack([m.v for m in assets.CAP_MESHES]),axis=0)

def directions(v):
 norm=np.linalg.norm(v,axis=1);v=v[norm>1e-10]/norm[norm>1e-10,None]
 return np.unique(np.round(v,8),axis=0)

def poly(mesh):
 tri=mesh.v[mesh.f]
 normals=directions(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]))
 edges=directions(np.vstack([tri[:,1]-tri[:,0],tri[:,2]-tri[:,1],tri[:,0]-tri[:,2]]))
 return np.unique(mesh.v,axis=0),normals,edges

BATTERY_PARTS=[poly(m) for m in assets.BATTERY_MESHES]
column_xy=TRAY_DATA['rim']+TRAY_XY
COLUMN=np.vstack([np.c_[column_xy,np.full(len(column_xy),z)] for z in (TOP-.2,RIM)])
COLUMN_N=np.vstack([np.c_[RIM_N,np.zeros(len(RIM_N))],[[0,0,1]]])
COLUMN_E=np.vstack([np.c_[RIM_E,np.zeros(len(RIM_E))],[[0,0,1]]])
COLUMN_LOW,COLUMN_HIGH=COLUMN.min(axis=0),COLUMN.max(axis=0)

def inside(points):return np.all((points[:,:2]-TRAY_XY)@RIM_N.T<=RIM_B+1e-7,axis=1)

def envelope(o,kind):return world(o,BATTERY_POINTS if kind=='battery' else CAP_POINTS)

def bounds(o,kind):
 p=envelope(o,kind)
 return p.min(axis=0),p.max(axis=0)

def protected(b,c):
 # A spatial broad phase avoids unnecessary transforms for unrelated covers.
 if np.linalg.norm(np.asarray(c.pos)-b.pos)>.13:return False
 rb,rc=rotation(b),rotation(c)
 relative=rc.T@rb
 delta=rc.T@(np.asarray(b.pos)-c.pos)
 # Analytic support of each complete terminal cylinder against every cavity plane.
 normal_local=CAVITY_N@relative
 radius=.0035*np.linalg.norm(normal_local[:,:2],axis=1)+.003*np.abs(normal_local[:,2])
 for x in (-.018,.018):
  centre=relative@np.array([x,0,.073])+delta
  if np.any(CAVITY_N@centre+radius>CAVITY_B+EPS):return False
 # The pedestal must really engage the bore. A hovering cap is insufficient.
 section=PEDESTAL_SECTION@relative.T+delta
 if np.any(section[:,:2]@BORE_N.T>BORE_B+ENGAGEMENT_CONTACT_EPS):return False
 if section[:,2].min()<.002-EPS or section[:,2].max()>.018+EPS:return False
 mouth=(world(c,MOUTH)-b.pos)@rb
 return bool(mouth[:,2].min()>=.060-EPS and mouth[:,2].max()<=.064+EPS)

def matching(objects):
 pairs=[[j for j in range(3) if protected(objects[f'battery{i}'],objects[f'cap{j}'])] for i in range(3)]
 # A physical cover can count for only one battery, irrespective of its identity.
 return [row if len(row)==1 and sum(row[0] in other for other in pairs)==1 else [] for row in pairs]

def enters(b):
 p=envelope(b,'battery')
 if np.any(p.max(axis=0)<=COLUMN_LOW+1e-7) or np.any(p.min(axis=0)>=COLUMN_HIGH-1e-7):return False
 if np.any(inside(p)&(p[:,2]<RIM-1e-7)&(p[:,2]>TOP-.2)):return True
 # Full convex separating-axis tests catch edge-only and tilted crossings.
 rb=rotation(b)
 for vertices,normals,edges in BATTERY_PARTS:
  p=vertices@rb.T+b.pos
  if np.any(p.max(axis=0)<=COLUMN_LOW+1e-7) or np.any(p.min(axis=0)>=COLUMN_HIGH-1e-7):continue
  cross=np.cross(COLUMN_E[:,None,:],(edges@rb.T)[None,:,:]).reshape(-1,3)
  axes=np.vstack([COLUMN_N,normals@rb.T,cross])
  axes=axes[np.linalg.norm(axes,axis=1)>1e-9]
  a=p@axes.T;bproj=COLUMN@axes.T
  if not np.any((a.max(axis=0)<=bproj.min(axis=0)+1e-7)|(bproj.max(axis=0)<=a.min(axis=0)+1e-7)):return True
 return False

def resting(o):return np.linalg.norm(o.lin_vel)<=.01 and np.linalg.norm(o.ang_vel)<=np.radians(5)

def placed(objects,i,pairs):
 if len(pairs[i])!=1:return False
 b,c=objects[f'battery{i}'],objects[f'cap{pairs[i][0]}']
 if not np.all(inside(envelope(b,'battery'))) or not np.all(inside(envelope(c,'cap'))):return False
 base=world(b,BASE)
 if base[:,2].min()<FLOOR-EPS or base[:,2].max()>FLOOR+.003:return False
 if rotation(b)[2,2]<np.cos(np.radians(5)):return False
 mouth=(world(c,MOUTH)-b.pos)@rotation(b)
 if mouth[:,2].max()>.063+EPS:return False
 return bool(resting(b) and resting(c))

def boxes_clear(a,b):
 return np.linalg.norm(np.maximum(np.maximum(a[0]-b[1],b[0]-a[1]),0))>=.03

class Scorer:
 def __init__(self,on_failure=None):
  self.on_failure=on_failure
  self.reset()

 def reset(self):
  self.bad=False;self.reason='';self.time=0.;self.hold=np.zeros(3)
  self.clear_since=[None]*3;self.pairs=[[],[],[]];self.open=False;self.pads=[]

 def fail(self,reason):
  if not self.bad:
   self.bad=True;self.reason=reason
   if self.on_failure:self.on_failure(self.time,reason)

 def check(self,objects):
  for name in NAMES:
   if name not in objects:self.fail('missing object state');return [[],[],[]]
   o=objects[name]
   if not np.isfinite(np.r_[o.pos,o.quat_xyzw,o.lin_vel,o.ang_vel]).all() or np.linalg.norm(o.quat_xyzw)<1e-8:
    self.fail('invalid object state');return [[],[],[]]
  pairs=matching(objects)
  for i in range(3):
   b=objects[f'battery{i}']
   if envelope(b,'battery')[:,2].min()<TOP-.05:self.fail('battery dropped below table')
   if not pairs[i] and enters(b):self.fail('unprotected battery entered storage')
  t=objects['storage_tray']
  if np.linalg.norm(np.asarray(t.pos)-np.r_[TRAY_XY,TOP])>.001 or rotation(t)[2,2]<np.cos(np.radians(1)):
   self.fail('fixed tray moved')
  return pairs

 def step(self,objects,dt):
  if dt<0 or not np.isfinite(dt):raise ValueError('invalid elapsed time')
  self.time+=dt
  self.pairs=self.check(objects)
  if self.bad:self.hold[:]=0;return
  for i in range(3):
   if placed(objects,i,self.pairs):self.hold[i]+=dt
   else:self.hold[i]=0;self.clear_since[i]=None

 def release_clear(self,objects,i,pairs):
  # Clearance establishes release for this pack, regardless of jaw aperture elsewhere.
  if len(self.pads)!=4 or not pairs[i]:return False
  for name,kind in [(f'battery{i}','battery'),(f'cap{pairs[i][0]}','cap')]:
   bb=bounds(objects[name],kind)
   if any(not boxes_clear(pad,bb) for pad in self.pads):return False
  return True

 def observe_hands(self,objects,is_open,pads):
  self.open=bool(is_open);self.pads=pads
  pairs=self.check(objects)
  if self.bad:self.clear_since=[None]*3;return
  for i in range(3):
   if placed(objects,i,pairs) and self.release_clear(objects,i,pairs):
    if self.clear_since[i] is None:self.clear_since[i]=self.time
   else:self.clear_since[i]=None

 def value(self,objects):
  pairs=self.check(objects)
  if self.bad:return 0.
  n=0
  for i in range(3):
   if not placed(objects,i,pairs) or not self.release_clear(objects,i,pairs):
    self.hold[i]=0;self.clear_since[i]=None
    continue
   if self.hold[i]>=1.-1e-8 and self.clear_since[i] is not None and self.time-self.clear_since[i]>=1.-1e-8:n+=1
  return n/3.
