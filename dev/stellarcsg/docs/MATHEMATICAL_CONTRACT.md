# Initial mathematical contract for the periodic radial surface

Status: executable prototype contract for the first bounded kernel; not yet the final OpenMC surface contract.

## Coordinates and orientation

For Cartesian point \(\mathbf{x}=(x,y,z)\), define

\[
R=\sqrt{x^2+y^2},\qquad \varphi=\operatorname{atan2}(y,x).
\]

A periodic reference axis supplies \(R_a(\varphi)\), \(Z_a(\varphi)\) and their toroidal derivatives. Define

\[
q_R=R-R_a(\varphi),\qquad q_Z=z-Z_a(\varphi),
\]
\[
\rho=\sqrt{q_R^2+q_Z^2},\qquad
\theta=\operatorname{atan2}(q_Z,q_R).
\]

The surface field supplies positive radius \(\rho_s\) and derivatives
\(\rho_{s,\theta}\), \(\rho_{s,\varphi}\). The implicit function is

\[
F(\mathbf{x})=\rho-\rho_s(\theta,\varphi).
\]

The negative half-space is the interior. This is not a signed-distance function when the radius varies with angle.

## Derivatives

Away from \(R=0\) and \(\rho=0\),

\[
\rho_R=\frac{q_R}{\rho},\quad
\rho_z=\frac{q_Z}{\rho},\quad
\rho_\varphi=-\frac{q_R R'_a+q_Z Z'_a}{\rho},
\]

\[
\theta_R=-\frac{q_Z}{\rho^2},\quad
\theta_z=\frac{q_R}{\rho^2},\quad
\theta_\varphi=\frac{q_Z R'_a-q_R Z'_a}{\rho^2}.
\]

Therefore

\[
F_R=\rho_R-\rho_{s,\theta}\theta_R,
\]
\[
F_z=\rho_z-\rho_{s,\theta}\theta_z,
\]
\[
F_\varphi=\rho_\varphi-\rho_{s,\theta}\theta_\varphi-\rho_{s,\varphi}.
\]

The Cartesian gradient is

\[
F_x=F_R\frac{x}{R}-F_\varphi\frac{y}{R^2},\qquad
F_y=F_R\frac{y}{R}+F_\varphi\frac{x}{R^2},\qquad
F_z=F_z.
\]

The outward normal is \(\nabla F/\lVert\nabla F\rVert\).

## Current admissible envelope

The prototype assumes:

- a finite conservative Cartesian bounding box;
- a positive, finite, single-valued \(\rho_s(\theta,\varphi)\);
- no surface self-intersection;
- no use of the gradient at \(R=0\) or on the reference axis \(\rho=0\);
- a ray direction that is finite and nonzero.

The compiler-level star-shapedness, Jacobian, nesting, curvature, and seam checks are not yet implemented.

## Reference distance contract

For ray \(\mathbf{x}(t)=\mathbf{x}_0+t\mathbf{\Omega}\), the distance routine searches the complete finite interval produced by ray / bounding-box intersection. It considers:

- sign-changing brackets of \(G(t)=F(\mathbf{x}(t))\);
- sampled near-zero values;
- stationary points bracketed through \(G'(t)=\nabla F\cdot\mathbf{\Omega}\), to detect tangent roots.

Candidates are refined, deduplicated, and the nearest positive candidate is returned. A coincident start is pushed by a scale-aware positive distance before searching.

This prototype does **not** yet certify absence of roots between samples. The production contract must replace that weakness with conservative patch subdivision, interval bounds, or another proof-producing method, while keeping this implementation as one independent reference path.
