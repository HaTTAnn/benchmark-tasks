"""Author rigid photography-station props and fictional document artwork."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from usdkit import Look, box, cylinder, collider, write_usda
HERE=Path(__file__).resolve().parent
TEX=HERE/'textures'; TEX.mkdir(exist_ok=True)
FONT='DejaVuSans.ttf'
BOLD='DejaVuSans-Bold.ttf'
def texture(name,w,h,rows,bg='white'):
    im=Image.new('RGB',(w,h),bg); d=ImageDraw.Draw(im)
    for text,y,size,color,bold in rows:
        d.text((w/2,y),text,font=ImageFont.truetype(BOLD if bold else FONT,size),fill=color,anchor='mt')
    im.save(TEX/name)
texture('document.png',700,900,[
 ('INTERNAL ONLY',45,76,'#a72531',True),
 ('NOT FOR CUSTOMER',190,57,'#a72531',True),
 ('DISTRIBUTION',265,66,'#a72531',True),
 ('MUG — UNIT COST',425,60,'#252c38',True),
 ('$4.80',535,155,'#182a3a',True),
 ('FICTIONAL SAMPLE',835,26,'#7b8791',False)])
texture('send.png',800,240,[('SEND PHOTO',25,73,'#edf5ff',True),('LEFT WRIST CAMERA',130,38,'#b9cedd',False)],'#243849')
LOOKS={
 'board':Look(color=(.18,.095,.045),roughness=.75),
 'paper':Look(color=(.94,.94,.90),roughness=.9),
 'metal':Look(color=(.36,.39,.42),metallic=.8,roughness=.3),
 'navy':Look(color=(.025,.075,.15),roughness=.62),
 'grip':Look(color=(.17,.24,.30),roughness=.68),
 'base':Look(color=(.045,.065,.085),roughness=.6),
 'button':Look(color=(.025,.34,.30),roughness=.4),
 'surface':Look(color=(.49,.53,.55),roughness=.88)}
def label(path,root,filename,sx,sy,z,cx=0,cy=0):
    # Page top is world +X and page left is +Y, toward the native camera.
    p=[(cx-sx/2,cy+sy/2,z),(cx-sx/2,cy-sy/2,z),(cx+sx/2,cy-sy/2,z),(cx+sx/2,cy+sy/2,z)]
    text=f'''
    def Material "LabelMaterial" {{
        token outputs:surface.connect = </{root}/LabelMaterial/Surface.outputs:surface>
        def Shader "Surface" {{
            uniform token info:id = "UsdPreviewSurface"
            color3f inputs:diffuseColor.connect = </{root}/LabelMaterial/Texture.outputs:rgb>
            float inputs:roughness = 0.85
            token outputs:surface
        }}
        def Shader "UV" {{
            uniform token info:id = "UsdPrimvarReader_float2"
            token inputs:varname = "st"
            float2 outputs:result
        }}
        def Shader "Texture" {{
            uniform token info:id = "UsdUVTexture"
            asset inputs:file = @textures/{filename}@
            token inputs:sourceColorSpace = "sRGB"
            token inputs:wrapS = "clamp"
            token inputs:wrapT = "clamp"
            float2 inputs:st.connect = </{root}/LabelMaterial/UV.outputs:result>
            float3 outputs:rgb
        }}
    }}
    def Mesh "PrintedFace" (prepend apiSchemas = ["MaterialBindingAPI"]) {{
        point3f[] points = {p}
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0,1,2,3]
        texCoord2f[] primvars:st = [(0,0),(1,0),(1,1),(0,1)] (interpolation = "vertex")
        uniform token subdivisionScheme = "none"
        uniform bool doubleSided = true
        rel material:binding = </{root}/LabelMaterial>
    }}
'''
    s=path.read_text(); path.write_text(s[:s.rfind('}')]+text+'}\n')
def make(name,root,parts,bounds):
    path=HERE/(name+'.usda')
    write_usda(str(path),root,parts,LOOKS,[collider('Collision'+str(i),size,center,root) for i,(size,center) in enumerate(bounds)],mass=.2)
    return path
doc=make('document','Document',[
 ('Board',box((.23,.175,.007),(0,0,.0035),bevel=.001,round_xy=.007),'board'),
 ('Paper',box((.205,.155,.001),(-.004,0,.0075)),'paper'),
 ('Clip',box((.018,.065,.010),(.102,0,.012),bevel=.002,round_xy=.003),'metal')],
 [((.23,.175,.008),(0,0,.004)),((.018,.065,.010),(.102,0,.012))])
label(doc,'Document','document.png',.195,.148,.0081,cx=-.008)
# Scale the clipboard to a compact desk note while retaining readable artwork.
from pxr import Usd, UsdGeom, Gf
stage_doc=Usd.Stage.Open(str(doc))
UsdGeom.Xformable(stage_doc.GetDefaultPrim()).AddScaleOp().Set(Gf.Vec3f(.75,.75,.75))
stage_doc.GetRootLayer().Save()
doc.write_text(doc.read_text().rstrip() + '\n')
make('cover','Cover',[
 ('FolderFace',box((.20,.15,.005),(0,0,.0025),bevel=.001,round_xy=.004),'navy'),
 ('RaisedSpine',box((.19,.018,.021),(0,.061,.014),bevel=.002,round_xy=.002),'grip'),
 ('PaperEdge',box((.185,.002,.002),(0,-.074,.003)),'paper')],
 [((.20,.15,.006),(0,0,.003)),((.19,.018,.021),(0,.061,.014))])
base=make('control_base','Base',[
 ('Housing',box((.10,.12,.024),(0,0,.012),bevel=.003,round_xy=.009),'base'),
 ('ButtonRim',cylinder(.027,.004,(-.018,0,.026)),'metal')],
 [((.10,.12,.014),(0,0,.007)),((.029,.12,.010),(.0355,0,.019)),
  ((.071,.026,.010),(-.0145,.047,.019)),((.071,.026,.010),(-.0145,-.047,.019))])
label(base,'Base','send.png',.028,.105,.0241,cx=.029)
cap=make('control_cap','Cap',[
 ('ButtonCap',cylinder(.022,.010,(-.018,0,.031),bevel=.002),'button')],
 [((.036,.036,.010),(-.018,0,.031))])
# A fixed base and a spring-return plunger. Only joint compression fires a capture.
from pxr import Usd, UsdGeom, UsdPhysics, Gf
stage=Usd.Stage.CreateNew(str(HERE/'send_control.usda'))
root=UsdGeom.Xform.Define(stage,'/SendControl'); stage.SetDefaultPrim(root.GetPrim())
UsdGeom.SetStageUpAxis(stage,'Z'); UsdGeom.SetStageMetersPerUnit(stage,1.)
b=stage.DefinePrim('/SendControl/base','Xform'); b.GetReferences().AddReference('control_base.usda')
UsdPhysics.ArticulationRootAPI.Apply(b)
c=stage.DefinePrim('/SendControl/cap','Xform'); c.GetReferences().AddReference('control_cap.usda')
UsdPhysics.MassAPI.Apply(c).CreateMassAttr(.025)
f=UsdPhysics.FixedJoint.Define(stage,'/SendControl/fixed'); f.CreateBody0Rel().SetTargets([root.GetPath()]); f.CreateBody1Rel().SetTargets([b.GetPath()])
j=UsdPhysics.PrismaticJoint.Define(stage,'/SendControl/press')
j.CreateBody0Rel().SetTargets([b.GetPath()]); j.CreateBody1Rel().SetTargets([c.GetPath()])
j.CreateAxisAttr('Z'); j.CreateLowerLimitAttr(-.006); j.CreateUpperLimitAttr(0.)
d=UsdPhysics.DriveAPI.Apply(j.GetPrim(),'linear')
d.CreateTypeAttr('force'); d.CreateStiffnessAttr(300.); d.CreateDampingAttr(2.)
d.CreateTargetPositionAttr(0.); d.CreateMaxForceAttr(20.)
stage.GetRootLayer().Save()
control_path = HERE / 'send_control.usda'
control_path.write_text(control_path.read_text().rstrip() + '\n')
make('photo_surface','PhotoSurface',[
 ('Sweep',box((.35,.41,.0001),(0,0,0),round_xy=.008),'surface')],
 [((.35,.41,.0001),(0,0,0))])
print('Authored document, cover, physical send button and photo surface.')
