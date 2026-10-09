"""Bounded synthetic experiments, with candidates rather than certified hits.

All lengths here are metres. These models are research approximations; none
of the sampled fits is a whole-domain geometry or first-intersection proof.
"""

from dataclasses import dataclass
import math

import numpy as np
from scipy.linalg import eigh
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq

from fourier_torus import VmecBoundary, torus_ray_candidates


TAU = 2.0 * math.pi


def synthetic_boundary(amplitude=0.12):
    return VmecBoundary(3, np.array([0, 1, 1, 1]),
                        np.array([0, 0, 3, -3]),
                        np.array([5.0, 0.8, amplitude / 2, amplitude / 2]),
                        np.array([0.0, 0.8, amplitude / 2, amplitude / 2]))


def fourier_jet(boundary, theta, phi):
    """Position, first and second physical derivatives from Fourier modes."""
    m, n = boundary.xm, boundary.xn
    phase = m * theta - n * phi
    c, s = np.cos(phase), np.sin(phase)

    def component(cc, ss):
        if ss is None:
            ss = np.zeros_like(cc)
        value = cc * c + ss * s
        phase_derivative = -cc * s + ss * c
        return np.array([np.sum(value), np.sum(m * phase_derivative),
                         np.sum(-n * phase_derivative),
                         np.sum(-m * m * value), np.sum(m * n * value),
                         np.sum(-n * n * value)])

    r = component(boundary.rmnc_m, boundary.rmns_m)
    z = component(np.zeros_like(boundary.zmns_m) if boundary.zmnc_m is None
                  else boundary.zmnc_m, boundary.zmns_m)
    er = np.array([math.cos(phi), math.sin(phi), 0.0])
    ep = np.array([-math.sin(phi), math.cos(phi), 0.0])
    ez = np.array([0.0, 0.0, 1.0])
    p = r[0] * er + z[0] * ez
    dt = r[1] * er + z[1] * ez
    dp = r[2] * er + r[0] * ep + z[2] * ez
    dtt = r[3] * er + z[3] * ez
    dtp = r[4] * er + r[1] * ep + z[4] * ez
    dpp = (r[5] - r[0]) * er + 2.0 * r[2] * ep + z[5] * ez
    return p, dt, dp, dtt, dtp, dpp


def surface_frame(jet):
    p, dt, dp, dtt, dtp, dpp = jet
    normal = np.cross(dp, dt)
    size = np.linalg.norm(normal)
    if size < 1e-12:
        raise ValueError("degenerate surface Jacobian")
    normal = normal / size
    jac = np.column_stack((dt, dp))
    metric = jac.T @ jac
    second = -np.array([[normal @ dtt, normal @ dtp],
                        [normal @ dtp, normal @ dpp]])
    curvature, vectors = eigh(second, metric)
    directions = jac @ vectors
    return p, normal, curvature, directions


@dataclass
class TorusPatch:
    center: np.ndarray
    frame: np.ndarray  # local x, y, z columns in world coordinates
    major: float
    minor: float
    beta_center: float
    half_alpha: float = math.pi
    half_beta: float = math.pi

    @classmethod
    def osculating(cls, jet):
        p, n, curvature, directions = surface_frame(jet)
        positive = np.flatnonzero(curvature > 1e-10)
        if not len(positive):
            raise ValueError("no positive principal curvature")
        i = int(positive[np.argmax(curvature[positive])])
        k1, k2 = float(curvature[i]), float(curvature[1 - i])
        if abs(k2) < 1e-10:
            raise ValueError("zero curvature needs a cylinder/plane limit")
        minor = 1.0 / k1
        outer = k2 > 0.0
        major = 1.0 / k2 - minor if outer else minor + 1.0 / abs(k2)
        if major <= minor:
            raise ValueError("this fit does not admit a ring torus")
        radial = n if outer else -n
        axis = directions[:, i]
        axis = axis / np.linalg.norm(axis)
        parallel = np.cross(axis, radial)
        parallel /= np.linalg.norm(parallel)
        frame = np.column_stack((radial, parallel, axis))
        center = p - (major + minor if outer else major - minor) * radial
        return cls(center, frame, major, minor, 0.0 if outer else math.pi)

    def project(self, points):
        q = (np.asarray(points) - self.center) @ self.frame
        radius = np.hypot(q[..., 0], q[..., 1])
        radial = np.stack((q[..., 0] / radius, q[..., 1] / radius,
                           np.zeros_like(radius)), axis=-1)
        circle = self.major * radial
        tube = q - circle
        rho = np.linalg.norm(tube, axis=-1)
        nlocal = tube / rho[..., None]
        projected = circle + self.minor * nlocal
        return (self.center + projected @ self.frame.T,
                nlocal @ self.frame.T, rho - self.minor)

    def set_sampled_trims(self, points):
        q = (np.asarray(points) - self.center) @ self.frame
        alpha = np.arctan2(q[..., 1], q[..., 0])
        beta = np.arctan2(q[..., 2], np.hypot(q[..., 0], q[..., 1]) - self.major)
        delta = (beta - self.beta_center + math.pi) % TAU - math.pi
        self.half_alpha = float(np.max(np.abs(alpha))) + 1e-12
        self.half_beta = float(np.max(np.abs(delta))) + 1e-12

    def ray_candidates(self, origin, direction, ceiling):
        o = (np.asarray(origin) - self.center) @ self.frame
        d = np.asarray(direction) @ self.frame
        roots = torus_ray_candidates(o, d, self.major, self.minor,
                                    self.minor, ceiling)
        admitted = []
        for t in roots:
            q = o + t * d
            alpha = math.atan2(q[1], q[0])
            beta = math.atan2(q[2], math.hypot(q[0], q[1]) - self.major)
            delta = (beta - self.beta_center + math.pi) % TAU - math.pi
            if abs(alpha) <= self.half_alpha and abs(delta) <= self.half_beta:
                admitted.append(t)
        return tuple(admitted)


def fit_fourier_patch(boundary, theta, phi):
    """Recover admitted exact circular inputs, otherwise use local curvature.

    Curvatures alone do not uniquely determine a torus latitude. The general
    local fit selects an outer/inner equator representative; exact Fourier
    tori are dispatched separately so the control recovers the known surface.
    """
    i00 = np.flatnonzero((boundary.xm == 0) & (boundary.xn == 0))
    i10 = np.flatnonzero((boundary.xm == 1) & (boundary.xn == 0))
    if len(i00) == len(i10) == 1:
        r0, a = float(boundary.rmnc_m[i00[0]]), float(boundary.rmnc_m[i10[0]])
        rc, zs = np.zeros_like(boundary.rmnc_m), np.zeros_like(boundary.zmns_m)
        rc[i00[0]], rc[i10[0]], zs[i10[0]] = r0, a, a
        asymmetric_zero = all(v is None or np.all(v == 0)
                              for v in (boundary.rmns_m, boundary.zmnc_m))
        if r0 > a > 0 and asymmetric_zero and np.array_equal(rc, boundary.rmnc_m) and np.array_equal(zs, boundary.zmns_m):
            c, s = math.cos(phi), math.sin(phi)
            return TorusPatch(np.zeros(3), np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]), r0, a, theta)
    return TorusPatch.osculating(fourier_jet(boundary, theta, phi))


# Polynomial coefficients in normalized Cartesian coordinates, keyed by
# monomial powers. Every term of each circular torus polynomial has degree <=4.
def poly_add(a, b, factor=1.0):
    out = dict(a)
    for exponent, value in b.items():
        out[exponent] = out.get(exponent, 0.0) + factor * value
    return out


def poly_mul(a, b):
    out = {}
    for ea, va in a.items():
        for eb, vb in b.items():
            e = tuple(x + y for x, y in zip(ea, eb))
            out[e] = out.get(e, 0.0) + va * vb
    return out


def torus_polynomial(center, axis, major, minor):
    center, axis = np.asarray(center), np.asarray(axis)
    axis = axis / np.linalg.norm(axis)
    q, parallel = {}, {(0, 0, 0): -float(axis @ center)}
    for i in range(3):
        e = tuple(int(j == i) for j in range(3))
        linear = {e: 1.0, (0, 0, 0): -float(center[i])}
        q = poly_add(q, poly_mul(linear, linear))
        parallel[e] = float(axis[i])
    shifted = poly_add(q, {(0, 0, 0): major**2 - minor**2})
    transverse = poly_add(q, poly_mul(parallel, parallel), -1.0)
    return poly_add(poly_mul(shifted, shifted), transverse, -4.0 * major**2)


MONOMIALS = [(i, j, k) for i in range(5) for j in range(5 - i)
             for k in range(5 - i - j)]


def polynomial_vector(poly):
    return np.array([poly.get(e, 0.0) for e in MONOMIALS])


def polynomial_design(points):
    points = np.asarray(points)
    return np.column_stack([np.prod(points ** np.array(e), axis=-1) for e in MONOMIALS])


def compile_torus_sum(polynomials, weights):
    if len(polynomials) != len(weights):
        raise ValueError("one weight is needed for each polynomial")
    return sum((float(w) * polynomial_vector(p) for p, w in zip(polynomials, weights)),
               np.zeros(len(MONOMIALS)))


def polynomial_ray(coefficients, origin, direction):
    result = np.zeros(5)
    for value, exponent in zip(coefficients, MONOMIALS):
        term = np.array([value])
        for i, power in enumerate(exponent):
            for _ in range(power):
                term = np.polynomial.polynomial.polymul(term, (origin[i], direction[i]))
        result[:len(term)] += term
    return result


def real_quartic_candidates(coefficients, origin, direction, ceiling):
    ray = polynomial_ray(coefficients, origin, direction)
    return sorted(float(r.real) for r in np.polynomial.polynomial.polyroots(ray)
                  if abs(r.imag) < 1e-7 and 0 <= r.real <= ceiling)


class HybridRadius:
    """Exact torus plateaus with periodic cubic-Hermite radius joins.

    This is a separable synthetic surface, not a general tensor-product spline
    patch compiler. The radius, classifier and normal describe the same solid.
    """
    def __init__(self, count, fraction, amplitude=0.12):
        if count < 4 or not 0 < fraction <= 1:
            raise ValueError("count>=4 and 0<fraction<=1 required")
        self.count, self.fraction = count, fraction
        self.width = TAU / count
        self.half = (1 - fraction) * self.width / 2
        self.radii = 0.8 + amplitude * np.cos(3 * np.arange(count) * self.width)
        self.bound = float(np.max(self.radii))
        self.amplitude = amplitude

    def value_derivative(self, phi):
        phi = np.asarray(phi) % TAU
        j = np.floor((phi + self.half) / self.width).astype(int)
        q = phi - j * self.width
        s = np.clip((q - self.half) / (self.fraction * self.width), 0.0, 1.0)
        r0, r1 = self.radii[j % self.count], self.radii[(j + 1) % self.count]
        h = s * s * (3 - 2 * s)
        dh = 6 * s * (1 - s) / (self.fraction * self.width)
        return r0 + (r1 - r0) * h, (r1 - r0) * dh

    def patches(self):
        out = []
        for j in range(self.count):
            c = j * self.width
            if self.half > 0:
                out.append(ProfilePatch(c - self.half, c + self.half, "torus", float(self.radii[j]), self.bound))
            out.append(ProfilePatch(c + self.half, c + self.width - self.half, "spline", None, self.bound))
        return out

    def positional_error_bound(self):
        # Radius is a convex combination of adjacent sampled target radii.
        # |a'(phi)|<=3*|amplitude|; farther contributing node is at most
        # (1+fraction)*width/2 away, giving a same-parameter position bound.
        return min(2 * abs(self.amplitude),
                   3 * abs(self.amplitude) * self.width * (1 + self.fraction) / 2)


class SplineRadius:
    def __init__(self, count, amplitude=0.12):
        self.count = count
        nodes = np.linspace(0, TAU, count + 1)
        values = 0.8 + amplitude * np.cos(3 * nodes)
        values[-1] = values[0]
        self.spline = CubicSpline(nodes, values, bc_type="periodic")
        w = TAU / count
        # Power-basis triangle bound for the represented floating coefficients.
        self.bound = float(np.max(np.abs(self.spline.c).T @ np.array([w**3, w**2, w, 1])))

    def value_derivative(self, phi):
        phi = np.asarray(phi) % TAU
        return self.spline(phi), self.spline(phi, 1)

    def patches(self):
        w = TAU / self.count
        return [ProfilePatch(j * w, (j + 1) * w, "spline", None, self.bound)
                for j in range(self.count)]


def trig_bounds(lo, hi, cosine):
    fun = math.cos if cosine else math.sin
    values = [fun(lo), fun(hi)]
    offset = 0.0 if cosine else math.pi / 2
    for k in range(math.ceil((lo - offset) / math.pi), math.floor((hi - offset) / math.pi) + 1):
        values.append(fun(offset + k * math.pi))
    return min(values), max(values)


@dataclass
class ProfilePatch:
    lo: float
    hi: float
    kind: str
    radius: float | None
    max_radius: float

    def contains(self, phi):
        return (phi - self.lo) % TAU <= self.hi - self.lo + 1e-10

    def box(self):
        rlo, rhi = 5 - self.max_radius, 5 + self.max_radius
        ranges = []
        for cosine in (True, False):
            a, b = trig_bounds(self.lo, self.hi, cosine)
            products = [rlo * a, rlo * b, rhi * a, rhi * b]
            ranges.append((min(products), max(products)))
        pad = 1e-11
        return (np.array([ranges[0][0], ranges[1][0], -self.max_radius]) - pad,
                np.array([ranges[0][1], ranges[1][1], self.max_radius]) + pad)


def ray_box(origin, direction, lower, upper, ceiling):
    lo, hi = 0.0, ceiling
    for i in range(3):
        if abs(direction[i]) < 1e-16:
            if origin[i] < lower[i] or origin[i] > upper[i]:
                return None
        else:
            a, b = (lower[i] - origin[i]) / direction[i], (upper[i] - origin[i]) / direction[i]
            lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
        if lo > hi:
            return None
    return lo, hi


class SharedIndex:
    """One BVH for torus and spline patches; no first-root early termination."""
    def __init__(self, patches):
        self.patches = patches
        boxes = [p.box() for p in patches]
        def build(ids):
            lower = np.min([boxes[i][0] for i in ids], axis=0)
            upper = np.max([boxes[i][1] for i in ids], axis=0)
            if len(ids) <= 2:
                return lower, upper, ids, None
            axis = int(np.argmax(upper - lower))
            ids = sorted(ids, key=lambda i: (boxes[i][0][axis] + boxes[i][1][axis]) / 2)
            mid = len(ids) // 2
            return lower, upper, None, (build(ids[:mid]), build(ids[mid:]))
        self.root = build(list(range(len(patches))))

    def candidates(self, origin, direction, ceiling):
        counters = {"box_tests": 0, "torus_candidates": 0, "spline_candidates": 0,
                    "quartic_solves": 0, "scalar_evaluations": 0}
        admitted, stack = [], [self.root]
        while stack:
            lower, upper, ids, children = stack.pop()
            counters["box_tests"] += 1
            if ray_box(origin, direction, lower, upper, ceiling) is None:
                continue
            if children is not None:
                stack.extend(children)
            else:
                for i in ids:
                    lower, upper = self.patches[i].box()
                    counters["box_tests"] += 1
                    interval = ray_box(origin, direction, lower, upper, ceiling)
                    if interval is not None:
                        admitted.append((self.patches[i], interval))
        return admitted, counters


def profile_normal(theta, phi, radius, derivative):
    er = np.array([math.cos(phi), math.sin(phi), 0.0])
    ep = np.array([-math.sin(phi), math.cos(phi), 0.0])
    ez = np.array([0.0, 0.0, 1.0])
    dt = radius * (-math.sin(theta) * er + math.cos(theta) * ez)
    dp = derivative * (math.cos(theta) * er + math.sin(theta) * ez) + (5 + radius * math.cos(theta)) * ep
    normal = np.cross(dp, dt)
    return normal / np.linalg.norm(normal)


def profile_field(point, profile):
    x, y, z = point
    phi = math.atan2(y, x)
    radius = float(profile.value_derivative(phi)[0])
    return (math.hypot(x, y) - 5)**2 + z*z - radius*radius


def query_diagnostic(profile, index, origin, direction, ceiling=20.0):
    """Return candidate distances and work counters, never a certified HIT."""
    origin, direction = np.asarray(origin), np.asarray(direction)
    admitted, counters = index.candidates(origin, direction, ceiling)
    roots = []
    for patch, (lo, hi) in admitted:
        if patch.kind == "torus":
            counters["torus_candidates"] += 1
            counters["quartic_solves"] += 1
            seeds = torus_ray_candidates(origin, direction, 5, patch.radius, patch.radius, ceiling)
        else:
            counters["spline_candidates"] += 1
            def f(t):
                counters["scalar_evaluations"] += 1
                return profile_field(origin + t * direction, profile)
            samples = np.linspace(lo, hi, 33)
            values = [f(t) for t in samples]
            seeds = []
            for j in range(len(samples) - 1):
                if values[j] == 0:
                    seeds.append(samples[j])
                if values[j] * values[j + 1] < 0:
                    seeds.append(brentq(f, samples[j], samples[j + 1], xtol=1e-12))
        for t in seeds:
            point = origin + t * direction
            if patch.contains(math.atan2(point[1], point[0])):
                roots.append((float(t), patch.kind))
    first = min(roots, key=lambda r: r[0]) if roots else None
    return {"disposition": "UNRESOLVED", "candidate_distance": first[0] if first else None,
            "candidate_kind": first[1] if first else None,
            "bound_candidate_count": len(admitted), "counters": counters,
            "reason": "sampled root search and numerical bounds are not completeness certificates"}
