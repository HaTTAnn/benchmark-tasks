# Scoring definition

## Safety failures

Failure is checked at every 240 Hz physics step, before any credit. A failure permanently sets the trial score to 0. Turning OFF or repairing the scene does not clear it; only an actual new-trial reset does.

A trial fails if:

- The actual knob angle is strictly above 30 degrees while any part of the spatula contacts the burner. Reintroduced contact while ON also fails.
- Any part of the pan or spatula falls more than 5 cm below the tabletop.
- The fixed burner or knob base moves more than 1 mm or tilts more than 1 degree.
- A geometry state is invalid or non-finite.

Burner contact is overlap between the complete spatula solid and a closed vertical cylinder of radius 11 cm, extending 2 mm above and below the highest burner surface. An airborne spatula entirely outside this height band is not in contact. There is no 5 cm overhead exclusion zone. The contact test includes triangle interiors, edges and solid containment. Closed radial and vertical boundaries use a 1 pm arithmetic tolerance; this adds no physical clearance margin.

## Safely parked spatula

All conditions must hold continuously for 1 second:

- The complete spatula is inside the original solid tabletop bounds: x=[-0.19,0.91], y=[-0.65,0.65] m.
- Every surface point's horizontal projection is at least 5 cm beyond the burner's circular edge.
- The lowest point of its actual PhysX-cooked collision solid is 0-2 mm above the tabletop, with at most 0.05 mm downward solver tolerance.
- Its local thickness axis is within 5 degrees of vertical, so it lies flat. Its entire surface need not be below 1 cm.
- It is independently supported on the cold table. The complete surface is at least 2 mm from the pan, burner/mounting plate and knob solids.
- Both complete gripper collision solids, including palms, fingers and pads, are at least 3 cm from the complete spatula. No jaw opening is required.
- Every point on the spatula surface moves at most 1 cm/s, including motion from rotation.

Discarding the spatula cannot satisfy parking. In a diagnostic initial state where it already qualifies, it need not be moved again.

## Placed pan

All conditions must hold continuously for 1 second:

- Bottom centre within 2 cm horizontally of the burner centre.
- Axis within 5 degrees of vertical.
- Bottom centre 0-5 mm above the highest burner surface, with at most 0.05 mm downward solver tolerance.
- Linear speed at most 1 cm/s and angular speed at most 5 degrees/s.
- Both complete gripper collision solids at least 3 cm from the complete pan and handle. No jaw opening is required.

## Score

If no failure occurred, use mutually exclusive ending-state scores:

| Condition | Score |
|---|---:|
| Spatula safely parked, pan placed, knob >30 degrees, and both complete grippers at least 3 cm from the complete spatula, pan/handle and knob solids; all together continuously for 1 second | 1.0 |
| Spatula safely parked and pan placed, without full success | 0.5 |
| Spatula safely parked, pan not placed | 0.25 |
| Every other outcome | 0.0 |

Partial credit uses the ending state, without accumulating historical milestones. Either placement order is allowed, but the spatula must clear before activation. The visible LED, unsafe-activation test and completion use the same strictly >30-degree ON threshold. Use the complete video and pointer/LED history to audit activation; a final photo alone cannot establish safe history.

## Geometry implementation

At reset, actual cooked convex vertices for spatula support and complete gripper release are read once through the official read-only API. A failed or invalid query prevents scoring, with no simplified fallback. The original visible spatula mesh defines complete bounds, surface velocity and burner contact. The monitor reads fresh rigid-body poses at each physics step. No disassembly or deletion action is available.

Cooked-versus-visible support approximations are documented in [TECHNICAL.md](TECHNICAL.md).
