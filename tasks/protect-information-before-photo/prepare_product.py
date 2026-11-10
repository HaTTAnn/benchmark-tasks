"""Prepare the Arena YCB mug mesh with a uniform teal material."""
from pathlib import Path
import tempfile
from urllib.request import urlretrieve
import numpy as np
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf,UsdPhysics
SOURCE='https://omniverse-content-staging.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/IsaacLab/Arena/assets/object_library/srl_robolab_assets/objects/ycb/mug.usd'
HERE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as td:
    src=Path(td)/'mug.usd';urlretrieve(SOURCE,src)
    stage=Usd.Stage.Open(str(src))
    mesh=next(UsdGeom.Mesh(p) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh))
    world=UsdGeom.XformCache().GetLocalToWorldTransform(mesh.GetPrim())
    points=np.asarray([world.Transform(Gf.Vec3d(*p)) for p in mesh.GetPointsAttr().Get()])
    lo,hi=points.min(0),points.max(0)
    scale=.125/max((hi-lo)[:2])
    points=(points-np.array([(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]]))*scale
    out=Usd.Stage.CreateNew(str(HERE/'product.usda'))
    UsdGeom.SetStageUpAxis(out,UsdGeom.Tokens.z);UsdGeom.SetStageMetersPerUnit(out,1)
    root=UsdGeom.Xform.Define(out,'/Product').GetPrim();out.SetDefaultPrim(root)
    UsdPhysics.RigidBodyAPI.Apply(root);UsdPhysics.MassAPI.Apply(root).CreateMassAttr(.2)
    m=UsdGeom.Mesh.Define(out,'/Product/Mug')
    m.CreatePointsAttr([Gf.Vec3f(*p) for p in points])
    m.CreateFaceVertexCountsAttr(mesh.GetFaceVertexCountsAttr().Get())
    m.CreateFaceVertexIndicesAttr(mesh.GetFaceVertexIndicesAttr().Get())
    m.CreateSubdivisionSchemeAttr('none')
    UsdPhysics.CollisionAPI.Apply(m.GetPrim())
    UsdPhysics.MeshCollisionAPI.Apply(m.GetPrim()).CreateApproximationAttr('convexHull')
    mat=UsdShade.Material.Define(out,'/Product/Looks/Teal')
    sh=UsdShade.Shader.Define(out,'/Product/Looks/Teal/Surface');sh.CreateIdAttr('UsdPreviewSurface')
    sh.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set((.012,.285,.34))
    sh.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.28)
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(),'surface')
    UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(mat)
    out.GetRootLayer().Save()
    print('Prepared library mug; metres:',np.round(points.max(0)-points.min(0),4),'vertices:',len(points))
