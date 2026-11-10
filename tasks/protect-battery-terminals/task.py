"""Three intact battery dummies, two bare and one protected, three green insulating cups, and a library-derived coated-metal low-wall storage tray. Install the caps before storing the batteries; cap retention uses gravity/contact only."""
from __future__ import annotations
import os,sys,pathlib,json,itertools
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import steptime,build_assets,physics_monitor,scenekit,layout
from scenekit import UsdBody,on_reset,on_step,arm_joints,robot_links
from yam_arena.task_file import TABLE_TOP
from yam_arena.demo import Waypoint,pick_place_waypoints
from yam_arena.constants import FINGER_OPEN
from yam_arena.urdf import quat_xyzw_to_matrix
build_assets.make()
HANDLE_OFFSET=build_assets.HANDLE_OFFSET
SCENE='station';TOP=TABLE_TOP[SCENE];SUCCESS_HOLD_S=0.0
START=list(layout.BATTERY_XY)
CAP_START=list(layout.CAP_XY)
DEST=list(layout.PARKING_XY)
TRAY_XY=np.array(layout.TRAY_XY);_tray=np.load(pathlib.Path(__file__).parent/'library_tray.npz');FLOOR=TOP+float(_tray['floor_height']);RIM=TOP+float(_tray['rim_height'])
RIM_POLYGON=_tray['rim'];_edge=np.roll(RIM_POLYGON,-1,axis=0)-RIM_POLYGON
POLY_N=np.c_[_edge[:,1],-_edge[:,0]];POLY_N/=np.linalg.norm(POLY_N,axis=1)[:,None]
POLY_B=np.sum(POLY_N*RIM_POLYGON,axis=1)
_worldrim=RIM_POLYGON+TRAY_XY
COLUMN_V=np.vstack([np.c_[_worldrim,np.full(len(_worldrim),z)] for z in (TOP-.2,RIM)])
COLUMN_N=np.vstack((np.c_[POLY_N,np.zeros(len(POLY_N))],[[0,0,1]]))
COLUMN_E=np.vstack((np.c_[_edge,np.zeros(len(_edge))],[[0,0,1]]))
BATTERIES=[UsdBody(f'battery{i}',pos=(*p,TOP+.0005),size=(.100,.0568,.076),mass=.25,usd='battery.usda',friction=(1.2,1.0),torsional_patch=.015,solver_iters=32) for i,p in enumerate(START)]
CAPS=[UsdBody(f'cap{i}',pos=(*p,TOP+.0005+layout.CAP_Z_OFFSETS[i]),size=(.070,.044,.0346),mass=.025,usd='cap.usda',friction=(.8,.7),torsional_patch=.01,solver_iters=32) for i,p in enumerate(CAP_START)]
TRAY=UsdBody('storage_tray',pos=(*TRAY_XY,TOP),size=(.337,.495,.02141),usd='tray.usda',mass=None)
OBJECTS=[*BATTERIES,*CAPS,TRAY]
import battery_scoring as scoring
_names=scoring.NAMES
_event_file=None
_control=0

def failure_event(time,reason):
 print('SAFETY_FAILURE',round(time,5),reason,flush=True)
 if _event_file:
  with open(_event_file,'a') as f:f.write(json.dumps({'time_s':time,'event':reason})+'\n')

ENGINE=scoring.Scorer(failure_event)

@on_reset
def reset(environment):
 global _event_file,_control
 ENGINE.reset();steptime.reset();_control=0
 root=os.environ.get('TASK_SCORE_DIR');_event_file=None
 if root:
  pathlib.Path(root).mkdir(parents=True,exist_ok=True)
  epoch=getattr(reset,'epoch',0);reset.epoch=epoch+1
  _event_file=str(pathlib.Path(root)/f'events-{os.getpid()}-{epoch}.jsonl')
 physics_monitor.install(environment,physics_update)


def physics_update(environment,dt):
 import torch
 station=environment.unwrapped.scene
 tensors=[]
 for name in _names:
  data=station[name].data
  pose=getattr(data.root_link_pose_w,'torch',data.root_link_pose_w)[0]
  vel=getattr(data.root_vel_w,'torch',data.root_vel_w)[0]
  tensors.append(torch.cat((pose,vel)))
 poses=scenekit._np(torch.stack(tensors));origin=scenekit._np(station.env_origins[0])
 objects={n:scenekit.BodyState(pos=p[:3]-origin,quat_xyzw=p[3:7],lin_vel=p[7:10],ang_vel=p[10:13],low=p[:3]-origin,high=p[:3]-origin) for n,p in zip(_names,poses)}
 ENGINE.step(objects,float(dt))

@on_step
def observation(environment):
 global _control
 from yam_arena.scene import object_states
 station=environment.unwrapped.scene;origin=scenekit._np(station.env_origins[0])
 is_open=all(np.all(arm_joints(environment,side,['joint7','joint8'])<=-.035) for side in ('left','right'))
 mesh_bounds={
  'tip_left':(np.array((-.02,.02317602,-.2199426))+np.array((.00999321,-.0914614,.129783)),np.array((.048,.09474682,-.1261))+np.array((.00999321,-.0914614,.129783))),
  'tip_right':(np.array((-.02,-.00194787,-.2199426))+np.array((-.0379932,-.00133753,.129783)),np.array((.048,.06962293,-.1261))+np.array((-.0379932,-.00133753,.129783)))}
 pads=[]
 for side in ('left','right'):
  robot=station[f'{side}_robot'];poses=scenekit._np(robot.data.body_pose_w)[0]
  for name in ('tip_left','tip_right'):
   p=poses[robot.body_names.index(name)];lo,hi=mesh_bounds[name]
   points=scoring.box(lo,hi)@quat_xyzw_to_matrix(p[3:7]).T+p[:3]-origin
   pads.append((points.min(axis=0),points.max(axis=0)))
 objects=object_states(environment,_names)
 ENGINE.observe_hands(objects,is_open,pads)
 steptime.tick();_control+=1
 if _control%20==0:
  print('BATTERY_STATE',round(ENGINE.time,3),json.dumps({'positions':{n:np.round(o.pos,5).tolist() for n,o in objects.items()},'pairs':ENGINE.pairs,'hold_s':ENGINE.hold.tolist(),'clear_since':ENGINE.clear_since,'open':ENGINE.open,'score':ENGINE.value(objects),'failure':ENGINE.reason}),flush=True)


def success(objects):return ENGINE.value(objects)==1.
def score(objects):return ENGINE.value(objects)


def demo():
 """Fixed open-loop Cartesian plans; no state-dependent commands."""
 mode=os.environ.get('TASK_DEMO','success')
 plans={}
 if mode=='layout':return {}
 if mode in ('failure','unsafe_entry','unsafe_repair'):
  x,y=START[0];dx,dy=DEST[0]
  plans['left']=pick_place_waypoints((x,y,TOP+.048),(dx,dy,FLOOR+.0485),travel_z=TOP+.12,yaw=0.,speed=.65)
  if mode=='unsafe_repair':
   cx,cy=CAP_START[0]
   plans['left']+=pick_place_waypoints((cx,cy,TOP+.037),(.338,.107,FLOOR+.0975),travel_z=TOP+.135,yaw=0.,speed=.65)
 elif mode in ('partial_one','cap_loss'):
  x,y=START[2];dx,dy=DEST[2]
  plans['left']=pick_place_waypoints((x,y,TOP+.048),(dx,dy,FLOOR+.0485),travel_z=TOP+.105,yaw=0.,speed=.6)
  if mode=='cap_loss':
   plans['left'] += pick_place_waypoints((.335,-.024,FLOOR+.097),(.15,0,TOP+.037),travel_z=TOP+.105,yaw=0.,speed=.6)
 else:
  for side,i in [('left',0),('right',1)]:
   x,y=START[i];cx,cy=CAP_START[i];dx,dy=DEST[i]
   plan=pick_place_waypoints((cx,cy,TOP+.037),(x,y,TOP+.0975),travel_z=TOP+.135,yaw=0.,speed=.65)
   plan += [Waypoint(1.,(x,y,TOP+.135),FINGER_OPEN,'cover settled',0.)]
   plan += pick_place_waypoints((x,y,TOP+.048),(dx,dy,FLOOR+.0485),travel_z=TOP+.12,yaw=0.,speed=.65)
   park=(.15,.36 if side=='left' else -.36,TOP+.14)
   plan += [Waypoint(2.,park,FINGER_OPEN,'park clear',0.),Waypoint(2.,park,FINGER_OPEN,'observe stored pack',0.)]
   plans[side]=plan
  if mode=='success':
   x,y=START[2];dx,dy=DEST[2]
   plans['left']+=pick_place_waypoints((x,y,TOP+.048),(dx,dy,FLOOR+.0485),travel_z=TOP+.105,yaw=0.,speed=.6)
  elif mode!='partial_two':raise ValueError(f'Unknown TASK_DEMO: {mode}')
 for side,plan in plans.items():
  park=(.15,.36 if side=='left' else -.36,TOP+.14)
  plan += [Waypoint(2.,park,FINGER_OPEN,'final park',0.),Waypoint(5.,park,FINGER_OPEN,'observe endpoint',0.)]
 return plans
