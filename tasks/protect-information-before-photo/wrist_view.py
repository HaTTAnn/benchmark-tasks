"""Open-loop demonstration: move from standard READY to a wrist viewing pose."""
import numpy as np
import os
from dataclasses import dataclass
from yam_arena.constants import READY
from yam_arena.ik import smoothstep

VIEW_MOVE_SECONDS = 20.0 if os.environ.get('TASK_DEMO') == 'moving_capture' else 4.0

def viewing_joints(t):
    start = np.asarray(READY, dtype=float)
    return start + smoothstep(t / VIEW_MOVE_SECONDS) * (np.asarray(TEST_VIEW_JOINTS.get(os.environ.get("TASK_DEMO"), LEFT_VIEW_JOINTS)) - start)

LEFT_VIEW_JOINTS = [-0.645858355312001, 1.1200189922059456, 1.2156456633053636, -0.8134448110041523, -0.011833420396136959, -0.8375118553990504]


@dataclass
class ViewHold:
    duration: float
    pos: tuple = (0.,0.,0.)
    finger: float = -.048
    label: str = 'hold left wrist view'
    yaw: float = 0.

def hold_plan(duration):
    """The demo explicitly commands the viewing joints; no controller is added to the task."""
    from yam_arena.demo import ArmPlan
    from yam_arena.ik import tcp_pose
    if not getattr(ArmPlan,'_view_hold',False):
        original_action,original_target=ArmPlan.action7,ArmPlan.target
        def action(self,t):
            if self.waypoints and isinstance(self.waypoints[0],ViewHold):
                return np.r_[viewing_joints(t),1.], ('move to wrist view' if t < VIEW_MOVE_SECONDS else 'hold left wrist view')
            return original_action(self,t)
        def target(self,t):
            if self.waypoints and isinstance(self.waypoints[0],ViewHold):
                p,r=tcp_pose(viewing_joints(t),self.base_pos)
                return p,r,-.048,'hold left wrist view'
            return original_target(self,t)
        ArmPlan.action7,ArmPlan.target=action,target
        ArmPlan._view_hold=True
    return [ViewHold(duration)]

# Fixed open-loop camera poses used only by visibility counterexamples.
TEST_VIEW_JOINTS = {'cup_small': [-1.0435775340922924, 1.02325098806216, 1.9135642231018137, -1.5854041803289964, -0.4498252488582327, -1.0728685800726243], 'cup_cropped': [-0.7526524076368755, 1.2750608983044704, 1.3889948952670905, -1.181671492146991, -0.5071664413738215, -0.5778751463609689]}

TEST_VIEW_JOINTS.update({'cup_edge_inside': [-0.7442909187302257, 1.258888704729376, 1.3723822742216762, -1.1451331299616057, -0.4627517580248566, -0.595734937266056], 'cup_size_above': [-0.5702430958017728, 1.174715094794268, 1.7154142070646439, -1.2742553505791308, 0.00957002174779225, -0.759180402364799], 'cup_size_below': [-0.4444407020625153, 0.768667072665155, 1.2426436318365945, -1.0589772757505598, 0.114630822675794, -0.7883626289553299]})

TEST_VIEW_JOINTS['safe_small'] = TEST_VIEW_JOINTS['cup_small']

TEST_VIEW_JOINTS['safe_cropped'] = TEST_VIEW_JOINTS['cup_cropped']
