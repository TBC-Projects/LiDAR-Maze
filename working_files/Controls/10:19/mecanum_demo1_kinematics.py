import numpy as np
import sympy as sp
from scipy.optimize import least_squares

# Frame: x forward, y left, counter-clockwise rotation positive.
# Wheel order: FL, FR, RL, RR. Roller axis angle delta (deg): FL/RR = +45, FR/RL = -45.
WHEELS = {"FL": (+1, +1, +45), "FR": (+1, -1, -45),
          "RL": (-1, +1, -45), "RR": (-1, -1, +45)}


def jacobian(L, W, r, phi_deg=0.0):
    """General 4x3 Jacobian: wheel speeds (rad/s) = J @ [vx, vy, wz].
    phi_deg is the mounting angle of every wheel (0 = axles parallel, the standard layout)."""
    rows = []
    for sx, sy, d in WHEELS.values():
        x, y = sx * L, sy * W
        a, dl = np.radians(phi_deg + d), np.radians(d)
        rows.append(np.array([np.sin(a), -np.cos(a), -y * np.sin(a) - x * np.cos(a)])
                    / (r * np.sin(dl)))
    return np.array(rows)


def test_mecanum_kinematics():
    # Robot parameters (m)
    r = 0.04   # wheel radius
    L = 0.07   # half wheelbase (front/back wheel centers are at x = +/-L)
    W = 0.13   # half track (left/right wheel centers are at y = +/-W)
    k = L + W

    # Test 1: Inverse kinematics (body velocity -> wheel speeds)
    J = (1 / r) * np.array([[1, -1, -k],
                            [1,  1,  k],
                            [1,  1, -k],
                            [1, -1,  k]])

    wheels_forward = J @ np.array([0.2, 0.0, 0.0])
    wheels_strafe = J @ np.array([0.0, 0.2, 0.0])
    wheels_spin = J @ np.array([0.0, 0.0, 1.0])
    print("Forward 0.2 m/s    -> wheel rad/s:", wheels_forward)
    print("Strafe left 0.2 m/s -> wheel rad/s:", wheels_strafe)
    print("Spin 1 rad/s CCW   -> wheel rad/s:", wheels_spin)

    assert np.allclose(wheels_forward, [5, 5, 5, 5]), "Forward motion failed"
    assert np.allclose(wheels_strafe, [-5, 5, 5, -5]), "Strafe motion failed"
    assert np.allclose(wheels_spin, [-5, 5, -5, 5]), "Spin motion failed"

    # Test 2: The general Jacobian (position + mounting angle) matches the standard one
    assert np.allclose(jacobian(L, W, r), J), "General Jacobian does not match standard J"

    # Test 3: Forward kinematics (wheel speeds -> body velocity) with the pseudoinverse
    v_body = np.array([0.15, -0.10, 0.5])
    v_recovered = np.linalg.pinv(J) @ (J @ v_body)
    print("Forward kinematics recovered body velocity:", v_recovered)
    assert np.allclose(v_recovered, v_body), "Forward kinematics failed"

    # 4 wheels but only 3 degrees of freedom: inconsistent wheel speeds mean slip
    w_bad = np.array([5.0, 0.0, 0.0, 0.0])
    slip = np.linalg.norm(w_bad - J @ (np.linalg.pinv(J) @ w_bad))
    print("Slip residual for inconsistent wheel speeds:", slip)
    assert slip > 1e-6, "Inconsistent wheel speeds should leave a residual"

    # Test 4: Can the robot move in any direction? (holonomic check)
    rank = np.linalg.matrix_rank(J)
    print("rank(J) =", rank)
    assert rank == 3, "Robot is not holonomic"

    # Test 5: Symbolic derivation with SymPy
    x, y, rs, phi, delta = sp.symbols("x y r phi delta", real=True)
    vx, vy, wz = sp.symbols("v_x v_y omega_z", real=True)
    Ls, Ws = sp.symbols("L W", positive=True)
    a = phi + delta
    w_sym = (sp.sin(a) * (vx - wz * y) - sp.cos(a) * (vy + wz * x)) / (rs * sp.sin(delta))

    print("\nSymbolic wheel speeds (phi = 0):")
    expected = {"FL": (vx - vy - (Ls + Ws) * wz), "FR": (vx + vy + (Ls + Ws) * wz),
                "RL": (vx + vy - (Ls + Ws) * wz), "RR": (vx - vy + (Ls + Ws) * wz)}
    for name, (sx, sy, d) in WHEELS.items():
        row = w_sym.subs({phi: 0, delta: sp.rad(d), x: sx * Ls, y: sy * Ws})
        row = sp.simplify(row)
        print(f"  w_{name} =", row)
        assert sp.simplify(row - expected[name] / rs) == 0, f"Symbolic row {name} failed"

    # Test 6: Solve for body velocity from measured wheel speeds (SymPy, then least squares)
    w_meas = J @ np.array([0.2, 0.1, 0.4])   # pretend these came from encoders
    eqs = [sp.Eq(float(J[i, 0]) * vx + float(J[i, 1]) * vy + float(J[i, 2]) * wz,
                 float(w_meas[i])) for i in range(3)]
    sol = sp.solve(eqs, [vx, vy, wz])
    print("\nSymPy solution (3 wheels):", sol)

    def residuals(v):
        return J @ v - w_meas
    result = least_squares(residuals, [0.0, 0.0, 0.0])
    print("Least squares solution (4 wheels):", result.x)
    assert np.allclose(result.x, [0.2, 0.1, 0.4], atol=1e-6), "Least squares failed"
    assert np.allclose([float(sol[vx]), float(sol[vy]), float(sol[wz])],
                       [0.2, 0.1, 0.4], atol=1e-6), "SymPy solve failed"

    # Test 7: Mounting angle sweep. phi = 0 is the best-conditioned layout.
    def cond(phi_deg):
        Jn = jacobian(L, W, r, phi_deg) @ np.diag([1.0, 1.0, 1.0 / k])  # yaw as rim speed
        return np.linalg.cond(Jn)

    print("\nMounting angle sweep (cond = 1 is ideal):")
    for p in [0, 15, 30, 45]:
        print(f"  phi = {p:2d} deg -> cond(J) = {cond(p):.2f}")
    assert np.isclose(cond(0), 1.0), "Standard layout should have cond(J) = 1"
    assert cond(30) > cond(0), "Angled mounting should not beat the standard layout"

    print("All Mecanum kinematics tests passed!")


# Run the Mecanum kinematics tests
test_mecanum_kinematics()
