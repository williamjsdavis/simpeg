import unittest
import discretize
from simpeg import utils, maps
from simpeg.utils.model_builder import get_indices_sphere
from simpeg.potential_fields import magnetics as mag
import numpy as np


class MagFwdProblemTests(unittest.TestCase):
    def setUp(self):
        Inc = 45.0
        Dec = 45.0
        Btot = 51000

        self.b0 = mag.analytics.IDTtoxyz(-Inc, Dec, Btot)

        cs = 25.0
        hxind = [(cs, 5, -1.3), (cs / 2.0, 41), (cs, 5, 1.3)]
        hyind = [(cs, 5, -1.3), (cs / 2.0, 41), (cs, 5, 1.3)]
        hzind = [(cs, 5, -1.3), (cs / 2.0, 40), (cs, 5, 1.3)]
        M = discretize.TensorMesh([hxind, hyind, hzind], "CCC")

        chibkg = 0.0
        self.chiblk = 0.01
        chi = np.ones(M.nC) * chibkg

        self.rad = 100
        self.sphere_center = [0.0, 0.0, 0.0]
        sph_ind = get_indices_sphere(self.sphere_center, self.rad, M.gridCC)
        chi[sph_ind] = self.chiblk

        xr = np.linspace(-300, 300, 41)
        yr = np.linspace(-300, 300, 41)
        X, Y = np.meshgrid(xr, yr)
        Z = np.ones((xr.size, yr.size)) * 150
        self.components = ["bx", "by", "bz"]
        self.xr = xr
        self.yr = yr
        self.rxLoc = np.c_[utils.mkvc(X), utils.mkvc(Y), utils.mkvc(Z)]
        receivers = mag.Point(self.rxLoc, components=self.components)
        srcField = mag.UniformBackgroundField(
            receiver_list=[receivers],
            amplitude=Btot,
            inclination=Inc,
            declination=Dec,
        )

        self.survey = mag.Survey(srcField)

        self.sim = mag.simulation.Simulation3DDifferential(
            M,
            survey=self.survey,
            muMap=maps.ChiMap(M),
        )
        self.M = M
        self.chi = chi

    def test_ana_forward(self):
        u = self.sim.fields(self.chi)
        dpred = self.sim.projectFields(u)

        bxa, bya, bza = mag.analytics.MagSphereAnaFunA(
            self.rxLoc[:, 0],
            self.rxLoc[:, 1],
            self.rxLoc[:, 2],
            self.rad,
            *self.sphere_center,
            self.chiblk,
            self.b0,
            "secondary",
        )

        n_obs, n_comp = self.rxLoc.shape[0], len(self.components)
        dx, dy, dz = dpred.reshape(n_comp, n_obs)

        err_x = np.linalg.norm(dx - bxa) / np.linalg.norm(bxa)
        err_y = np.linalg.norm(dy - bya) / np.linalg.norm(bya)
        err_z = np.linalg.norm(dz - bza) / np.linalg.norm(bza)

        self.assertLess(err_x, 0.08)
        self.assertLess(err_y, 0.08)
        self.assertLess(err_z, 0.08)


if __name__ == "__main__":
    unittest.main()
