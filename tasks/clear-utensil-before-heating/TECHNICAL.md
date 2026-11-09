# Technical reference

## Exact setup

Use the official station, both YAM arms, GPU PhysX at 240 Hz and control at 20 Hz. The robots, cameras, table and harness are unchanged. Coordinates are in metres: x points forward, y points to the robot's left, and the solid tabletop is at z=0.7475, spanning x=[-0.19,0.91] and y=[-0.65,0.65].

One fixed black metal burner disk, 0.22 m in diameter, is centred at (0.36,0). Its original mesh comes from furniture_sim under Apache-2.0. After scaling, the disk is approximately 12.63 mm thick. It rests on a 0.36 x 0.25 x 0.004 m metal mounting plate centred at (0.31,0), with the plate's underside on the tabletop. The highest burner surface is at approximately z=0.76413. A real metal backing surface, 0.75 mm below the highest rings, supports the exposed ring area. An upward-facing physical rotary knob is mounted immediately in front of the disk, at (0.21,0), on the same plate. Its approximately 54.6 mm diameter visual mesh is from the same source, with separately authored simple collision geometry. OFF is 0 degrees; clockwise angles strictly greater than 30 degrees, up to the 90-degree mechanical stop, mean ON. The pointer, OFF/ON markings and red LED are visible; ON is printed at the end of the dial's range. The knob does not overlap the spatula or pan handle.

The empty aluminium pan has a 0.16 m outside diameter, 0.06 m height, 0.4 kg mass, 3 mm bottom, 2 mm wall and phenolic-resin handle. Initially it rests flat at (0.36,-0.27), rotated Rz(-90 degrees), with the handle pointing toward world -x, downward in the top view. Its circular edge is initially 8 cm from the burner edge. The burner is 6 cm wider than the pan, leaving an exposed radial ring 3 cm wide. The reference policy's nominal final pan-bottom centre is (0.371313708,-0.011313708), offset 16 mm toward (+x,-y) within the 20 mm scoring tolerance. Its fixed open-loop placement includes a fixed placement-error compensation; the actual result must still meet the same 20 mm tolerance. This target preserves at least 5 mm of actual geometry clearance from the initial spatula, so pan placement does not push the spatula out of the way.

The rigid wooden spatula is NVIDIA SimReady Wooden_Spatula_B01, CC BY 4.0, retaining the original visual mesh, UV, wood texture, proportions and decomposed collision geometry. Its approximate dimensions are 0.2963 x 0.0692 x 0.0164 m and mass is 0.05154 kg, calculated from the solid mesh volume and a disclosed wood density of 700 kg/m^3. No extra handle is added. Local +x points toward the blade; the graspable handle near local x=-0.075 m is approximately 23 mm wide and 15 mm thick. The initial asset origin is (0.201372538,0.158627462,0.754828863), with rotation Rz(-45 degrees) times Ry(-3.684740315 degrees). It is naturally inclined, supported by both the tabletop and burner. The handle extends diagonally toward the open front-left tabletop (-x,+y), clear of the left arm's initial occlusion. The blade points radially toward the burner, with its innermost point approximately 8 cm from the burner centre: 3 cm of intrusion past the disk's rim. The disclosed final pan target maintains at least 5 mm clearance from the complete initial spatula. The reference demo vertically grasps the handle, lifts the whole spatula free, carries it through the air and releases it onto the cold table. It uses native fixed Waypoints and yaw, without pushing, attachment, binding, teleportation or hidden object-state feedback.

There is no required parking rectangle. Any solid cold-tabletop location satisfying the complete-geometry, independent-support, distance and stability conditions below is acceptable. Objects do not start on the table edge. A safe real-world reproduction uses an unplugged burner, empty cold pan, dry wooden spatula and low-voltage LED. Temperature, combustion and ignition are not simulated.

## Runtime and geometry

The official station, both YAM arms and three native cameras are unchanged. GPU physics runs at 240 Hz; control runs at 20 Hz. The layout is fixed (`object_jitter=0`).

Tested with Isaac Sim 6.1, IsaacLab-Arena 0.3.1 and Python 3.12. Runtime packages: NumPy 2.3.1, SciPy 1.17.0, trimesh 4.11.1 and Pillow 12.3.0. `pxr` and `omni.physx` come from Isaac Sim; CoACD is needed only for offline asset generation. Used meshes and textures are bundled with relative paths.

Wood friction is 0.8/0.6 static/dynamic; pan friction is 0.9/0.8. Original wood mesh, UV and proportions are retained, with textures reduced to 1024 pixels. Density 700 kg/m^3 gives mass 0.05154 kg. Planar subdivision converts 20 source convex pieces into 163 pieces with at most 64 vertices, preserving their union. Sampled collision deviations were below 2 mm; this is not a global mathematical bound. Cooked-versus-visible support differences measured 0.156 mm in flat parking and 0.668 mm in the initial incline, and depend on orientation.

The reference policy uses fixed native `Waypoint` trajectories with yaw. It grasps, lifts, carries and releases the spatula, then places the pan and turns the knob. It does not attach objects, write their poses or use hidden object-state feedback. The pan target includes fixed placement-error compensation; the actual pan must satisfy the same scoring tolerance.

## File map

| Files | Purpose |
|---|---|
| `task.py` | Scene, reference trajectory and terminal predicates |
| `monitor.py`, `scoring.py` | Physics-step safety history and whole-spatula contact |
| `handgeom.py`, `clearance.py`, `meshclearance.py`, `cooked_support.py` | Gripper release, surface separation and support geometry |
| `geometry.py`, USD/STL/NPZ files, `textures/` | Visual, collision and material assets |
| `scenekit.py`, `usdkit.py`, `steptime.py` | Scene helpers and optional timing diagnostics |

## Diagnostic configurations

These optional scripted configurations use the same scorer. Clear them before ordinary evaluation:

- `TASK_LEAVE_WOOD=1`: leave wood in burner contact during activation; expected score 0.
- `TASK_DEMO=failure`: activate unsafely and then repair the arrangement; expected score 0.
- `TASK_SAFE_INITIAL=1`: start with the spatula already safely parked.
- `TASK_DEMO=closed_low`: nominal 45-degree knob turn and jaw closure after release.

## Asset sources

- Wooden spatula: NVIDIA SimReady `Wooden_Spatula_B01`, CC BY 4.0; see `NOTICE.txt`, `LICENSE.txt` and `asset-manifest.json`.
- Burner/knob meshes: `vikashplus/furniture_sim`, commit `c97995afb81c9e2d7325b0069f9abc9a2c74a2f0`, Apache-2.0; see `furniture-sim-NOTICE.md` and `furniture-sim-LICENSE`.
- Locally authored pan, mounting and original task contributions: see `LICENSE-original-MIT.txt` and its scope in `LICENSING.md`.
- Reused helpers: see `shared-helpers-NOTICE.txt` and `LICENSING.md`. Third-party rights and notices remain in force.
