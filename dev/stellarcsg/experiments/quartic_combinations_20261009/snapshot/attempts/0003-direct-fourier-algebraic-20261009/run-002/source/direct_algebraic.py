"""Synthetic radial Fourier and local full-quartic experiments, in metres.

Numerical candidates are always UNRESOLVED: sampled stationary-point searches
and floating polynomial roots are not complete first-intersection certificates.
"""

from dataclasses import dataclass
import importlib.util
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from patch_methods import MONOMIALS, polynomial_design, polynomial_ray


INPUTS = Path(__file__).resolve().parents[1] / "attempts/0003-direct-fourier-algebraic-20261009/inputs"


def incumbent_spline():
    """Load the frozen repository evaluator, without importing its package."""
    spec = importlib.util.spec_from_file_location("frozen_incumbent_spline", INPUTS / "incumbent_spline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DirectFourier:
    """Known positive radial chart; stored n already includes field periods."""
    def __init__(self, circular=False):
        self.m = np.array([0, 2, 1])
        self.n = np.array([0, 3, -6])
        self.c = np.array([0.8, 0.0 if circular else 0.12, 0.0])
        self.s = np.array([0.0, 0.0, 0.0 if circular else 0.025])
        self.bound = float(np.sum(np.abs(self.c) + np.abs(self.s)))
        # This constructor's lower coefficient bound is positive; arbitrary
        # VMEC poloidal coefficients cannot be inserted into this radial chart.
        assert self.c[0] > np.sum(np.abs(self.c[1:]) + np.abs(self.s[1:]))

    def radius(self, theta, phi):
        theta, phi = np.broadcast_arrays(theta, phi)
        phase = theta[..., None] * self.m - phi[..., None] * self.n
        value = self.c * np.cos(phase) + self.s * np.sin(phase)
        derivative = -self.c * np.sin(phase) + self.s * np.cos(phase)
        return value.sum(axis=-1), (derivative * self.m).sum(axis=-1), (-derivative * self.n).sum(axis=-1)


class IncumbentBicubic:
    """Actual frozen bicubic radius evaluator; constant axis handled identically."""
    def __init__(self, target, nt, np_):
        self.module = incumbent_spline()
        t, p = np.meshgrid(2*np.pi*np.arange(nt)/nt, (2*np.pi/3)*np.arange(np_)/np_, indexing="ij")
        self.coefficients = self.module.samples_to_periodic_coefficients(target.radius(t, p)[0])
        self.bound = float(np.max(np.abs(self.coefficients)))

    def radius(self, theta, phi):
        return self.module.sample_periodic_bicubic(self.coefficients, theta, phi, 3)


def position(profile, theta, phi):
    theta, phi = np.broadcast_arrays(theta, phi)
    r = profile.radius(theta, phi)[0]
    R = 5.0 + r*np.cos(theta)
    return np.stack((R*np.cos(phi), R*np.sin(phi), r*np.sin(theta)), axis=-1)


def field_jet(profile, points):
    points = np.asarray(points, dtype=float)
    R = np.hypot(points[..., 0], points[..., 1])
    rho = np.hypot(R-5.0, points[..., 2])
    if np.any(R < 1e-12) or np.any(rho < 1e-12):
        raise ValueError("radial chart derivative singularity")
    phi = np.arctan2(points[..., 1], points[..., 0])
    theta = np.arctan2(points[..., 2], R-5.0)
    r, rt, rp = profile.radius(theta, phi)
    er = np.stack((points[..., 0]/R, points[..., 1]/R, np.zeros_like(R)), axis=-1)
    ep = np.stack((-points[..., 1]/R, points[..., 0]/R, np.zeros_like(R)), axis=-1)
    ez = np.zeros_like(points); ez[..., 2] = 1.0
    grad_rho = np.cos(theta)[..., None]*er + np.sin(theta)[..., None]*ez
    grad_theta = (-np.sin(theta)[..., None]*er + np.cos(theta)[..., None]*ez)/rho[..., None]
    gradient = grad_rho - rt[..., None]*grad_theta - rp[..., None]*ep/R[..., None]
    return rho-r, gradient


def normal(profile, points):
    grad = field_jet(profile, points)[1]
    return grad / np.linalg.norm(grad, axis=-1)[..., None]


def query_candidates(profile, origin, direction, ceiling=20.0, samples=257):
    """Diagnostic stationary splitting catches some even contacts, not all.

    Common algorithm for both representations. Never upgrades candidates,
    empty searches or singular charts into qualified HIT/NO_HIT results.
    """
    origin, direction = np.asarray(origin), np.asarray(direction)
    if origin.shape != (3,) or direction.shape != (3,) or not np.all(np.isfinite(np.r_[origin, direction])):
        raise ValueError("finite 3D ray required")
    if abs(np.linalg.norm(direction)-1) > 1e-10 or ceiling <= 0 or samples < 3:
        raise ValueError("unit direction, positive ceiling and >=3 samples required")
    counters = {"field_jet_points": 0, "stationary_candidates": 0, "scalar_refinements": 0}

    def evaluate(t):
        t = np.asarray(t)
        counters["field_jet_points"] += int(t.size)
        v, g = field_jet(profile, origin+t[..., None]*direction)
        return v, g @ direction

    def refine(fun, lo, hi):
        counters["scalar_refinements"] += 1
        return float(brentq(fun, lo, hi, xtol=2e-12))

    try:
        grid = np.linspace(0.0, ceiling, samples)
        values, derivatives = evaluate(grid)
        roots = []
        unsupported_intervals = []
        for i in range(samples-1):
            lo, hi = grid[i:i+2]
            splits = [lo, hi]
            if derivatives[i]*derivatives[i+1] < 0:
                try:
                    stationary = refine(lambda t: evaluate(t)[1], lo, hi)
                    counters["stationary_candidates"] += 1
                    splits.insert(1, stationary)
                except (ValueError, FloatingPointError) as e:
                    # A later unsupported chart interval must not discard an
                    # earlier candidate. It still prevents query certification.
                    unsupported_intervals.append({"lo_m":float(lo),"hi_m":float(hi),"reason":str(e)})
            vals = [values[i]] + ([evaluate(splits[1])[0]] if len(splits)==3 else []) + [values[i+1]]
            for t, v in zip(splits, vals):
                if abs(v) < 1e-10 and t > 1e-10:
                    roots.append(float(t))
            for j in range(len(splits)-1):
                if vals[j]*vals[j+1] < 0:
                    try:
                        roots.append(refine(lambda t: evaluate(t)[0], splits[j], splits[j+1]))
                    except (ValueError, FloatingPointError) as e:
                        unsupported_intervals.append({"lo_m":float(splits[j]),"hi_m":float(splits[j+1]),"reason":str(e)})
        roots = sorted(t for t in roots if t > 1e-10)
        unique = [t for i,t in enumerate(roots) if i==0 or t-roots[i-1] > 1e-7]
        return {"disposition": "UNRESOLVED", "candidates_m": unique,
                "candidate_distance_m": unique[0] if unique else None, "counters": counters,
                "unsupported": "some chart intervals unsupported" if unsupported_intervals else None,
                "unsupported_intervals": unsupported_intervals}
    except (ValueError, FloatingPointError) as e:
        return {"disposition": "UNRESOLVED", "candidates_m": [], "candidate_distance_m": None,
                "counters": counters, "unsupported": str(e), "unsupported_intervals": []}


def poly_gradient(coefficients, points):
    points = np.atleast_2d(points)
    result = np.zeros_like(points)
    for c, exponent in zip(coefficients, MONOMIALS):
        for axis, power in enumerate(exponent):
            if power:
                reduced = list(exponent); reduced[axis] -= 1
                result[:, axis] += c*power*np.prod(points**np.array(reduced), axis=-1)
    return result


@dataclass
class LocalQuartic:
    center: np.ndarray
    frame: np.ndarray
    scale: float
    coefficients: np.ndarray
    rank: int
    condition: float
    theta: float
    phi: float
    half_theta: float
    half_phi: float

    @classmethod
    def fit(cls, target, theta, phi, half_theta, half_phi):
        center = position(target, theta, phi)
        n = normal(target, center)
        # Poloidal tangent orthogonal to the common target normal.
        er = np.array([np.cos(phi), np.sin(phi), 0.0])
        tangent = -np.sin(theta)*er + np.cos(theta)*np.array([0.,0.,1.])
        tangent -= (tangent@n)*n; tangent /= np.linalg.norm(tangent)
        frame = np.column_stack((tangent, np.cross(n,tangent), n))
        scale = max(0.8*half_theta, (5+0.8)*half_phi)
        t,p = np.meshgrid(theta+np.linspace(-half_theta,half_theta,7), phi+np.linspace(-half_phi,half_phi,7), indexing="ij")
        points = position(target,t,p).reshape(-1,3)
        normals = normal(target,points)
        # Nonzero signed offset labels rule out the vacuous zero polynomial.
        cloud = np.concatenate([points+offset*scale*normals for offset in (-0.04,0.0,0.04)])
        labels = np.repeat([-0.04,0.0,0.04],len(points))
        design = polynomial_design((cloud-center)@frame/scale)
        coefficients,_,rank,singular = np.linalg.lstsq(design,labels,rcond=1e-12)
        return cls(center,frame,scale,coefficients,int(rank),float(singular[0]/singular[-1]),theta,phi,half_theta,half_phi)

    def ray_polynomial(self, origin, direction):
        return polynomial_ray(self.coefficients,(origin-self.center)@self.frame/self.scale,direction@self.frame/self.scale)

    def project_along(self, point, direction):
        ray = self.ray_polynomial(point,direction)
        roots = np.polynomial.polynomial.polyroots(ray)
        admitted = sorted((float(r.real) for r in roots if abs(r.imag)<1e-7 and abs(r.real)<0.2*self.scale),key=abs)
        if not admitted:
            return None, None, 0
        q = point+admitted[0]*direction
        grad = poly_gradient(self.coefficients,(q-self.center)@self.frame/self.scale)[0]@self.frame.T
        if np.linalg.norm(grad)<1e-12:
            return None,None,len(admitted)
        return q,grad/np.linalg.norm(grad),len(admitted)

    def trimmed_ray_candidates(self, origin, direction, ceiling=20.0):
        """Angular trim only: no closed atlas or global ownership guarantee."""
        roots = np.polynomial.polynomial.polyroots(self.ray_polynomial(origin,direction))
        admitted = []
        for root in roots:
            if abs(root.imag)>1e-7 or not 1e-10<root.real<=ceiling:
                continue
            point = origin+root.real*direction
            theta = np.arctan2(point[2],np.hypot(*point[:2])-5.0)
            phi = np.arctan2(point[1],point[0])
            dt = (theta-self.theta+np.pi)%(2*np.pi)-np.pi
            dp = (phi-self.phi+np.pi)%(2*np.pi)-np.pi
            if abs(dt)<=self.half_theta+1e-9 and abs(dp)<=self.half_phi+1e-9:
                admitted.append(float(root.real))
        return {"disposition":"UNRESOLVED","candidates_m":sorted(admitted)}
