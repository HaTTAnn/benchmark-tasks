"""Regression checks for disclosure latching and conservative projection."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from photo_scoring import EpisodeScore,privacy_measure


class EpisodeTests(unittest.TestCase):
    def test_disclosure_overrides_earlier_and_later_success(self):
        score=EpisodeScore()
        full={'diagnostic_category':'full_size'}
        self.assertEqual(score.record({'leak':False},full),1)
        self.assertEqual(score.record({'leak':True},full),0)
        self.assertEqual(score.record({'leak':False},full),0)

    def test_discard_after_success_is_irreversible(self):
        score=EpisodeScore(best_safe_photo=1)
        score.check_integrity([np.array([.4,.1,.75])],.7475)
        self.assertEqual(score.value,1)
        score.check_integrity([np.array([.4,.1,.6])],.7475)
        self.assertEqual(score.value,0)
        score.check_integrity([np.array([.4,.1,.75])],.7475)
        self.assertEqual(score.record({'leak':False},{'diagnostic_category':'full_size'}),0)

    def test_nonfinite_position_is_invalid(self):
        score=EpisodeScore(best_safe_photo=1)
        score.check_integrity([np.array([np.nan,0,.75])],.7475)
        self.assertEqual(score.value,0)

    def test_partial_credit_and_no_send(self):
        score=EpisodeScore()
        self.assertEqual(score.value,0)
        self.assertEqual(score.record({'leak':False},{'diagnostic_category':'incomplete'}),0)
        self.assertEqual(score.record({'leak':False},{'diagnostic_category':'small'}),.5)
        self.assertEqual(score.record({'leak':False},{'diagnostic_category':'incomplete'}),.5)

    def test_environment_reset_callback_clears_latch(self):
        import task
        task._SCORE=EpisodeScore(sends=3,leaked=True,best_safe_photo=1,invalid_scene=True)
        task._TRACK.update(step=20,armed=False,captures=3)
        task.reset_capture(None)
        self.assertEqual(task.score({}),0)
        self.assertFalse(task._SCORE.leaked)
        self.assertFalse(task._SCORE.invalid_scene)
        self.assertTrue(task._TRACK['armed'])
        self.assertEqual(task._TRACK['captures'],0)
        self.assertEqual(task._SCORE.record({'leak':False},{'diagnostic_category':'full_size'}),1)


class MugProjectionTests(unittest.TestCase):
    def test_both_size_thresholds_are_required(self):
        from cup_visibility import diagnostic_category
        base=dict(all_mesh_in_frame=True,silhouette_pixels=100,visible_fraction=1.,
                  largest_interior_occlusion_pixels=0)
        for height,area,expected in [(.30,.03,'full_size'),
                                     (.299999,.03,'small'),
                                     (.30,.029999,'small'),
                                     (.299999,.029999,'small')]:
            with self.subTest(height=height,area=area):
                result=diagnostic_category(dict(base,height_fraction=height,
                                                silhouette_area_fraction=area))
                self.assertEqual(result,expected)

    def test_camera_on_mesh_plane_fails_without_division_error(self):
        from cup_visibility import measure
        points=np.array([[0,0,0],[.01,0,.1],[0,.01,.1]])
        with np.errstate(divide='raise',invalid='raise'):
            result,*_=measure(points,np.array([[0,1,2]]),np.array([0,0,0,0,0,0,1.]),
                              np.zeros(3),np.array([0,0,0,1.]),np.eye(3),np.ones((10,10)))
        self.assertEqual(result['diagnostic_category'],'incomplete')


class PrivacyTests(unittest.TestCase):
    def test_single_exposed_panel_pixel_is_disclosure(self):
        pose=np.array([0,0,1,0,0,0,1.])
        args=(pose,np.zeros(3),np.array([0,0,0,1.]),
              np.array([[300,0,50],[0,300,50],[0,0,1.]]))
        _,panel=privacy_measure(*args,np.full((100,100),np.inf))
        depth=np.full((100,100),.98)
        self.assertFalse(privacy_measure(*args,depth)[0]['leak'])
        y,x=np.argwhere(panel)[len(np.argwhere(panel))//2]
        depth[y,x]=1.0081
        result,_=privacy_measure(*args,depth)
        self.assertEqual(result['exposed_panel_pixels'],1)
        self.assertTrue(result['leak'])

    def measure(self,depth,pose=None):
        if pose is None:pose=np.array([0,0,1,0,0,0,1.])
        return privacy_measure(pose,np.zeros(3),np.array([0,0,0,1.]),np.array([[300,0,50],[0,300,50],[0,0,1.]]),np.full((100,100),depth))[0]

    def test_exposed_covered_and_unknown_depth(self):
        self.assertTrue(self.measure(1.0081)['leak'])
        self.assertFalse(self.measure(.98)['leak'])
        self.assertTrue(self.measure(np.nan)['leak'])
        self.assertTrue(self.measure(0.)['leak'])

    def test_outside_frame_is_not_disclosure(self):
        self.assertFalse(self.measure(np.inf,np.array([10,0,1,0,0,0,1.]))['leak'])

    def test_near_plane_crossing_does_not_drop_visible_polygon(self):
        pose=np.array([0,0,.02,0,np.sin(np.pi/4),0,np.cos(np.pi/4)])
        self.assertTrue(self.measure(np.inf,pose)['leak'])


if __name__=='__main__':unittest.main()
