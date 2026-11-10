"""Original, dimensioned ABS battery test fixtures; meshes separate from contact geometry."""
from pathlib import Path
import numpy as np
import usdkit as u
import layout
HERE=Path(__file__).parent
HANDLE_OFFSET=0.0
LOOKS={'abs':u.Look((.075,.085,.095),roughness=.48),'lid':u.Look((.25,.39,.29),roughness=.52),'copper':u.Look((.72,.76,.80),metallic=.75,roughness=.22),'rubber':u.Look((.025,.025,.025),roughness=.9),'white':u.Look((.84,.84,.78),roughness=.65),'red':u.Look((.63,.035,.025),roughness=.5),'blue':u.Look((.035,.17,.34),roughness=.55)}
LOOKS.update({'lid_edge':u.Look((.075,.15,.10),roughness=.6),'lid_highlight':u.Look((.38,.51,.39),roughness=.55),'panel_light':u.Look((.78,.81,.77),roughness=.65)})
def cylcol(name,r,h,z,root,xy=(0,0)):
 return f'''\n    def Cylinder "{name}" (prepend apiSchemas = ["PhysicsCollisionAPI", "PhysxCollisionAPI", "MaterialBindingAPI"]) {{
        rel material:binding:physics = </{root}/PhysicsMaterial>
        uniform token purpose = "guide"
        double radius = {r}
        double height = {h}
        uniform token axis = "Z"
        float physxCollision:contactOffset = 0.001
        float physxCollision:restOffset = 0
        double3 xformOp:translate = ({xy[0]}, {xy[1]}, {z})
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }}'''
def bosscol(mesh,root,name="base_col"):
 xyz=', '.join('('+', '.join(f'{a:.7f}' for a in v)+')' for v in mesh.v)
 return f'''\n    def Mesh "{name}" (prepend apiSchemas = ["PhysicsCollisionAPI", "PhysicsMeshCollisionAPI", "PhysxCollisionAPI", "MaterialBindingAPI"]) {{
        rel material:binding:physics = </{root}/PhysicsMaterial>
        uniform token purpose = "guide"
        token visibility = "invisible"
        uniform token subdivisionScheme = "none"
        token physics:approximation = "convexHull"
        float physxCollision:contactOffset = 0.001
        float physxCollision:restOffset = 0
        point3f[] points = [{xyz}]
        int[] faceVertexCounts = [{', '.join('3' for _ in mesh.f)}]
        int[] faceVertexIndices = [{', '.join(str(int(i)) for i in mesh.f.reshape(-1))}]
    }}'''
def outline(sx,sy,r):
 return u._rounded_outline(sx,sy,r,seg=4)

def loft_rings(rings):
 """Surface between equal-length xy rings, including sloped annular walls."""
 n=len(rings[0]);vertices=np.vstack(rings);faces=[]
 for k in range(len(rings)-1):
  for i in range(n):
   j=(i+1)%n;a=k*n+i;b=k*n+j;c=(k+1)*n+j;d=(k+1)*n+i
   faces.extend(((a,b,c),(a,c,d)))
 return u.Mesh(vertices,np.asarray(faces))

def ring(xy,z):
 return np.c_[xy,np.full(len(xy),z)]

def make():
 global BATTERY_MESHES,CAP_MESHES
 root='Battery'
 shell=u.box((.100,.055,.060),(0,0,.030),bevel=.001,round_xy=.004)
 base_xy=outline(.060,.034,.003);top_xy=outline(.054,.028,.003)
 boss=loft_rings([ring(base_xy,.060),ring(base_xy,.066),ring(top_xy,.070)])
 boss=u.join(boss,u.prism(top_xy,.0695,.070),u.prism(base_xy,.060,.0605))
 parts=[('shell',shell,'abs'),('base_boot',u.box((.100,.055,.008),(0,0,.004),bevel=.0008,round_xy=.004),'rubber'),('lid_seam',u.box((.1002,.0552,.001),(0,0,.052),round_xy=.004),'rubber'),('top_lid',u.box((.098,.053,.006),(0,0,.057),bevel=.001,round_xy=.004),'abs'),('terminal_base',boss,'abs')]
 cols=[bosscol(shell,root,'body_col'),bosscol(boss,root)]
 for side in (-1,1):
  parts.append((f'grip_panel_{side+1}',u.box((.070,.0008,.028),(0,side*.0276,.030),bevel=.0002,round_xy=.0002),'rubber'))
  for k in range(9):
   parts.append((f'grip_rib_{side+1}_{k}',u.box((.002,.0012,.022),(-.028+k*.007,side*.0278,.030),bevel=.0003),'abs'))
 for i,x in enumerate((-.018,.018)):
  parts.append((f'terminal_collar{i}',u.cylinder(.005,.001,(x,0,.0705),segments=24),'red' if i else 'panel_light'))
  parts.append((f'terminal{i}',u.cylinder(.0035,.006,(x,0,.073),segments=24,bevel=.0003),'copper'))
  cols.append(cylcol(f'terminal_col{i}',.0035,.006,.073,root,(x,0)))
  parts.append((f'mark{i}',u.box((.008,.0015,.0004),(x,-.0095,.0702)), 'red' if i else 'white'))
  if i:parts.append(('plus',u.box((.0015,.007,.0004),(x,-.0095,.0702)),'red'))
 # High-contrast polarity panels remain visible on the shoulders beside the cover.
 for i,x in enumerate((-.041,.041)):
  parts.append((f'polarity_panel{i}',u.box((.013,.022,.0003),(x,0,.06015),round_xy=.001),'red' if i else 'panel_light'))
  parts.append((f'polarity_horizontal{i}',u.box((.010,.0025,.0003),(x,0,.06045)),'white' if i else 'rubber'))
  if i:parts.append(('polarity_vertical',u.box((.0025,.010,.0003),(x,0,.06045)),'white'))
 BATTERY_MESHES=[mesh for _,mesh,_ in parts]
 u.write_usda(str(HERE/'battery.usda'),root,parts,LOOKS,cols,mass=.25,friction=(1.2,1.0))

 root='Cap'
 outer=outline(.070,.044,.005);inner=outline(.066,.040,.003);mouth=outline(.068,.042,.004)
 wall=loft_rings([ring(mouth,0),ring(outer,0),ring(outer,.018),ring(inner,.018),ring(inner,.003),ring(mouth,0)])
 roof=u.box((.070,.044,.002),(0,0,.019),bevel=.0003,round_xy=.005)
 ridge=u.box((.040,.014,.014),(0,0,.027),bevel=.001,round_xy=.004)
 parts=[('cover_wall',wall,'lid'),('roof',roof,'lid'),('integral_grip_ridge',ridge,'lid')]
 # Thin external material bands clarify the lower opening and the separate cover.
 edge=outline(.0702,.0442,.0051)
 parts.append(('moulded_lower_edge',loft_rings([ring(edge,.0004),ring(edge,.0024)]),'lid_edge'))
 parts.append(('upper_edge_highlight',loft_rings([ring(edge,.017),ring(edge,.018)]),'lid_highlight'))
 for k in range(7):
  parts.append((f'ridge_texture{k}',u.box((.0012,.011,.0005),(-.015+k*.005,0,.0341),bevel=.0002),'lid'))
 cols=[bosscol(roof,root,'roof_col'),bosscol(ridge,root,'ridge_col')]
 faces=np.array([(0,1,3),(0,3,2),(4,6,7),(4,7,5),(0,4,5),(0,5,1),(2,3,7),(2,7,6),(0,2,6),(0,6,4),(1,5,7),(1,7,3)])
 # Individual convex wall sectors preserve the genuinely hollow opening.
 for i in range(len(outer)):
  j=(i+1)%len(outer)
  for section,z0,z1,inside0,inside1 in [('entry',0,.003,mouth,inner),('wall',.003,.018,inner,inner)]:
   vertices=np.array([[*p,z] for z,inside in [(z0,inside0),(z1,inside1)] for pair in [(inside[i],inside[j]),(outer[i],outer[j])] for p in pair])
   cols.append(bosscol(u.Mesh(vertices,faces),root,f'{section}_{i}'))
 CAP_MESHES=[mesh for _,mesh,_ in parts]
 u.write_usda(str(HERE/'cap.usda'),root,parts,LOOKS,cols,mass=.025,friction=(.8,.7))
 # Reuse NVIDIA SimReady Tray_A01 geometry with disclosed x/y/z scale.
 root='Tray';g=np.load(HERE/'library_tray.npz');mesh=u.Mesh(g['vertices'],g['faces']);parts=[('library_tray',mesh,'tray_metal')]
 looks=dict(LOOKS);looks['tray_metal']=u.Look((.035,.075,.13),metallic=.35,roughness=.5)
 z=float(g['floor_height'])+.00025
 for i,(x,y) in enumerate((x-layout.TRAY_XY[0],y-layout.TRAY_XY[1]) for x,y in layout.PARKING_XY):
  for j,(sz,c) in enumerate([((.104,.001,.0003),(x,y-.0295,z)),((.104,.001,.0003),(x,y+.0295,z)),((.001,.059,.0003),(x-.052,y,z)),((.001,.059,.0003),(x+.052,y,z))]):parts.append((f'outline{i}_{j}',u.box(sz,c),'white'))
 # Exact separate triangle collision mesh for the fixed/kinematic tray.
 xyz=', '.join('('+', '.join(f'{a:.7f}' for a in v)+')' for v in mesh.v)
 indices=', '.join(str(int(i)) for i in mesh.f.reshape(-1))
 cols=[f'''
    def Mesh "contact_mesh" (prepend apiSchemas = ["PhysicsCollisionAPI", "PhysicsMeshCollisionAPI", "PhysxCollisionAPI", "MaterialBindingAPI"]) {{
        rel material:binding:physics = </{root}/PhysicsMaterial>
        uniform token purpose = "guide"
        token visibility = "invisible"
        uniform token subdivisionScheme = "none"
        uniform bool doubleSided = true
        token physics:approximation = "none"
        float physxCollision:contactOffset = 0.001
        float physxCollision:restOffset = 0
        point3f[] points = [{xyz}]
        int[] faceVertexCounts = [{', '.join('3' for _ in mesh.f)}]
        int[] faceVertexIndices = [{indices}]
    }}''']
 u.write_usda(str(HERE/'tray.usda'),root,parts,looks,cols,mass=.5)
