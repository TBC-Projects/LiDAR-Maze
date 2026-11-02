import numpy as np
import sympy as sp
from scipy.optimize import least_squares


def test_mecanum_mounting():
    # Design requirements (SI units: m, s, rad)
    corridor = 0.40       # maze corridor width
    clearance = 0.03      # clearance wanted on each side
    r = 0.04              # wheel radius
    wheel_width = 0.038
    rpm_free = 300        # motor free speed at the wheel
    safety = 0.7          # only use 70% of free speed
    v_max = 0.30          # desired translation speed
    w_max = 2.0           # desired yaw rate
    electronics = 0.15    # smallest chassis side that fits the battery, LiDAR, controller

    # Test 1: Usable wheel rim speed and the largest allowed L + W
    # Worst case is full diagonal translation (|vx| + |vy| = sqrt(2) * v) plus full yaw:
    #   rim_max = sqrt(2) * v_max + (L + W) * w_max
    rpm_limit = rpm_free * safety
    rim_max = r * rpm_limit * 2 * np.pi / 60
    k_max = (rim_max - np.sqrt(2) * v_max) / w_max
    print(f"Usable wheel rpm: {rpm_limit:.0f}, rim speed: {rim_max:.3f} m/s")
    print(f"Largest allowed L + W: {k_max * 1000:.1f} mm")
    assert k_max > 0, "Motors are too slow for this v_max and w_max"

    # Test 2: Solve for the mounting position symbolically
    # Unknowns: L (half wheelbase) and W (half track)
    #   eq1: overall width 2W + wheel_width fits the corridor with clearance on each side
    #   eq2: L + W equals the motor-limited maximum
    L_sym, W_sym = sp.symbols("L W", positive=True)
    eq1 = 2 * W_sym + wheel_width - (corridor - 2 * clearance)
    eq2 = (L_sym + W_sym) - k_max
    solution = sp.solve([eq1, eq2], [L_sym, W_sym], dict=True)[0]
    L_sol, W_sol = float(solution[L_sym]), float(solution[W_sym])
    print(f"SymPy solution: L = {L_sol * 1000:.1f} mm, W = {W_sol * 1000:.1f} mm")

    # Test 3: Least squares solution of the same equations
    def mounting_residuals(x):
        L, W = x
        return [2 * W + wheel_width - (corridor - 2 * clearance),
                (L + W) - k_max]

    result = least_squares(mounting_residuals, [0.05, 0.10])
    L_opt, W_opt = result.x
    print(f"Least squares solution: L = {L_opt * 1000:.1f} mm, W = {W_opt * 1000:.1f} mm")
    assert np.allclose([L_opt, W_opt], [L_sol, W_sol], atol=1e-6), "Solvers disagree"

    # Test 4: Physical sanity checks on the solution
    L, W = L_sol, W_sol
    chassis_side = 2 * (L + r)                  # wheels flush with the front/back edge
    gap = W - wheel_width / 2 - chassis_side / 2  # space between chassis wall and wheel
    print(f"Chassis side: {chassis_side * 1000:.0f} mm, wall-to-wheel gap: {gap * 1000:.1f} mm")
    assert L > r, "Front and back wheels would overlap"
    assert gap >= 0, "Wheels would overlap the chassis"
    assert chassis_side >= electronics, "Electronics will not fit; use a wider corridor or thinner wheels"

    # Test 5: Worst-case wheel speeds stay within the motor limit
    k = L + W
    J = (1 / r) * np.array([[1, -1, -k],
                            [1,  1,  k],
                            [1,  1, -k],
                            [1, -1,  k]])
    assert np.linalg.matrix_rank(J) == 3, "Layout is not holonomic"
    d = v_max / np.sqrt(2)
    worst = np.abs(J @ np.array([d, d, w_max])) * 60 / (2 * np.pi)   # rpm
    print("Diagonal + spin wheel rpm:", np.round(worst))
    assert np.max(worst) <= rpm_limit + 1e-6, "Wheel speed limit exceeded"

    # Wheel mounting positions (body frame: x forward, y left)
    print("\nWheel centers (mm), axles parallel to y, heading 0 deg:")
    for name, (sx, sy) in {"FL": (1, 1), "FR": (1, -1), "RL": (-1, 1), "RR": (-1, -1)}.items():
        print(f"  {name}: x = {sx * L * 1000:+.1f}, y = {sy * W * 1000:+.1f}")

    print("All Mecanum mounting tests passed!")


# Run the Mecanum mounting tests
test_mecanum_mounting()
