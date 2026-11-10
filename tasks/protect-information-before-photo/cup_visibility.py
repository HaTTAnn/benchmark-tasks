"""Diagnostic mug projection and depth visibility, separate from the task score."""
from pathlib import Path
import json
import numpy as np


def install_depth(scene):
    original=scene.env_cfg_callback
    def factory(control_hz=None):
        configure=original(control_hz)
        def configured(cfg):
            cfg=configure(cfg)
            cfg.scene.left_cam.data_types=['rgb','distance_to_image_plane']
            return cfg
        return configured
    scene.env_cfg_callback=factory


def array(value):
    return getattr(value,'torch',value).detach().cpu().numpy()


def rotation(q):
    from yam_arena.urdf import quat_xyzw_to_matrix
    return quat_xyzw_to_matrix(np.asarray(q))


def mesh():
    from pxr import Usd,UsdGeom
    stage=Usd.Stage.Open(str(Path(__file__).parent/'product.usda'))
    m=UsdGeom.Mesh(stage.GetPrimAtPath('/Product/Mug'))
    return np.asarray(m.GetPointsAttr().Get(),dtype=np.float64),np.asarray(m.GetFaceVertexIndicesAttr().Get(),dtype=np.int64).reshape(-1,3)


def raster(uv,z,triangles,height,width):
    depth=np.full((height,width),np.inf)
    for face in triangles:
        a,b,c=face
        if min(z[a],z[b],z[c])<=.01:continue
        x0,y0=uv[a];x1,y1=uv[b];x2,y2=uv[c]
        den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
        if abs(den)<1e-10:continue
        xmin=max(0,int(np.floor(min(x0,x1,x2))))
        xmax=min(width-1,int(np.ceil(max(x0,x1,x2))))
        ymin=max(0,int(np.floor(min(y0,y1,y2))))
        ymax=min(height-1,int(np.ceil(max(y0,y1,y2))))
        if xmin>xmax or ymin>ymax:continue
        yy,xx=np.mgrid[ymin:ymax+1,xmin:xmax+1]
        u=((y1-y2)*(xx+.5-x2)+(x2-x1)*(yy+.5-y2))/den
        v=((y2-y0)*(xx+.5-x2)+(x0-x2)*(yy+.5-y2))/den
        w=1-u-v
        inside=(u>=-1e-8)&(v>=-1e-8)&(w>=-1e-8)
        inverse=u/z[a]+v/z[b]+w/z[c]
        zz=np.divide(1.,inverse,out=np.full_like(inverse,np.inf),where=inverse>0)
        patch=depth[ymin:ymax+1,xmin:xmax+1]
        np.minimum(patch,np.where(inside,zz,np.inf),out=patch)
    return depth


def occlusion_regions(mask, blocked):
    """Separate coherent interior occlusion from silhouette-edge raster noise."""
    from scipy.ndimage import binary_erosion, label
    interior = binary_erosion(mask, iterations=2)
    components, count = label(blocked & interior)
    sizes = np.bincount(components.ravel())[1:]
    return {
        'interior_occluded_pixels': int((blocked & interior).sum()),
        'largest_interior_occlusion_pixels': int(sizes.max()) if count else 0,
    }


def diagnostic_category(metrics):
    """Mug-only classification; confidentiality determines the final task score."""
    if (not metrics['all_mesh_in_frame'] or metrics['silhouette_pixels'] == 0
            or metrics['visible_fraction'] < .99
            or metrics['largest_interior_occlusion_pixels'] >= 9):
        return 'incomplete'
    if metrics['height_fraction'] >= .30 and metrics['silhouette_area_fraction'] >= .03:
        return 'full_size'
    return 'small'


def measure(points,triangles,product_pose,camera_pos,camera_quat_ros,K,actual_depth):
    world=points@rotation(product_pose[3:]).T+product_pose[:3]
    view=(world-camera_pos)@rotation(camera_quat_ros)
    z=view[:,2]
    safe_z=np.where(np.abs(z)<1e-9,1e-9,z)
    uv=(view[:,:2]/safe_z[:,None])@K[:2,:2].T+K[:2,2]
    h,w=actual_depth.shape
    expected=raster(uv,z,triangles,h,w)
    mask=np.isfinite(expected)
    valid_depth=np.isfinite(actual_depth)&(actual_depth>0)
    matched=mask&valid_depth&(np.abs(actual_depth-expected)<=.002)
    blocked=mask&valid_depth&(actual_depth<expected-.002)
    unmatched=mask&~(matched|blocked)
    n=int(mask.sum())
    inside=bool((z>.01).all() and (z<20).all() and (uv[:,0]>=0).all() and (uv[:,0]<=w).all() and (uv[:,1]>=0).all() and (uv[:,1]<=h).all())
    result={'all_mesh_in_frame':inside,'projected_bounds_px':[uv.min(0).tolist(),uv.max(0).tolist()],
            'min_camera_depth_m':float(z.min()),'silhouette_pixels':n,'silhouette_area_fraction':n/(h*w),
            'height_fraction':float(np.ptp(uv[:,1])/h),'visible_fraction':float(matched.sum()/max(n,1)),
            'occluded_fraction':float(blocked.sum()/max(n,1)),'unmatched_fraction':float(unmatched.sum()/max(n,1)),
            'depth_tolerance_m':.002,'final_score':None}
    result.update(occlusion_regions(mask, blocked))
    result['diagnostic_category'] = diagnostic_category(result)
    return result,mask,matched,blocked,unmatched,uv


def capture_diagnostic(base,out,stem):
    from PIL import Image
    camera=base.scene['left_cam'];data=camera.data
    rgb=array(data.output['rgb'])[0,...,:3].astype('uint8')
    depth=array(data.output['distance_to_image_plane'])[0,...,0]
    pose=array(base.scene['product'].data.root_link_pose_w)[0]
    camera_pos=array(data.pos_w)[0];quat=array(data.quat_w_ros)[0];K=array(data.intrinsic_matrices)[0]
    points,faces=mesh()
    result,mask,visible,blocked,unknown,uv=measure(points,faces,pose,camera_pos,quat,K,depth)
    np.savez_compressed(out/(stem+'-geometry.npz'),product_pose=pose,camera_pos=camera_pos,camera_quat_ros=quat,K=K,depth=depth)
    overlay=rgb.copy()
    for region,color in [(visible,[0,220,70]),(blocked,[255,40,30]),(unknown,[255,210,0])]:
        overlay[region]=(.45*overlay[region]+.55*np.array(color)).astype('uint8')
    Image.fromarray(overlay).save(out/(stem+'-visibility.png'))
    Image.fromarray((mask*255).astype('uint8')).save(out/(stem+'-expected-mask.png'))
    (out/(stem+'-visibility.json')).write_text(json.dumps(result,indent=2)+'\n')
    return result
