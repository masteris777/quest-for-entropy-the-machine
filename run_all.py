"""Reproduce every mechanism number in "The Machine" (Quest for Entropy #2).

One command:

    python run_all.py

It builds the certified machine from the byte-identical lab mirror under machine/,
runs it, and CHECKS each number the article quotes against the freshly measured
value - printing measured vs expected and PASS/FAIL for every one.

Runtime: well under a minute on a laptop.

Scope: THIS PACK IS ABOUT THE MECHANISM. The twenty-question quantum exam and the
interference floor are episode 3's evidence and ship with episode 3; no exam lab is
pulled in here.

Nothing below computes a probability from a quantum formula. The machine compares
three lengths, keeps one integer, and rewrites its state from a bank of free-running
rotors. Every number printed is measured off that machine.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
M = ROOT / "machine"

# The certified fold, imported from the byte-identical mirror. Importing this module
# pulls the whole certified chain in exactly the order the research repo does:
#   100v2 -> 95 -> 94 -> {93v2, 91v2} -> 88   (93v2 also reads lab 92's frozen constants)
sys.path.insert(0, str(M / "100_repreparation_fold"))
import repreparation_fold_100_v2 as lab100  # noqa: E402

lab95 = lab100.lab95
lab94 = lab100.lab94
lab93 = lab100.lab93
lab91 = lab100.lab91

TWO_PI = 2 * np.pi

# ---- the certified run, exactly as Lab 100 v2 declares it -------------------
FRAME = 91          # the certified frame seed (lab91.haar_frame(91))
K = lab100.K        # 16 generators
N_CHANNELS = 6      # 6 channels per generator
T_FOLDS = 5000      # folds measured here (article's traced fold is at t = 1000)
T_TRACE = 1000      # the article's worked example


# ============================================================== helpers ======

class Report:
    def __init__(self):
        self.items = []

    def add(self, num, title, rows, ok, notes=()):
        self.items.append((num, title, rows, bool(ok), tuple(notes)))

    def render(self):
        width = 78
        print("\n" + "=" * width)
        print("ARTICLE NUMBERS vs THIS RUN'S MEASURED VALUES")
        print("=" * width)
        for num, title, rows, ok, notes in self.items:
            print(f"\n[{'PASS' if ok else 'FAIL'}] {num}. {title}")
            for label, measured, expected in rows:
                print(f"       {label}")
                print(f"           measured: {measured}")
                print(f"           expected: {expected}")
            for n in notes:
                print(f"       note: {n}")
        n_ok = sum(1 for *_, ok, _ in self.items if ok)
        return n_ok, len(self.items)


def is_squarefree_int(n):
    d = 2
    while d * d <= n:
        if n % (d * d) == 0:
            return False
        d += 1
    return True


def is_perfect_square(n):
    r = int(round(np.sqrt(float(n))))
    for c in (r - 2, r - 1, r, r + 1, r + 2):
        if c >= 0 and c * c == n:
            return True
    return False


def circ(x):
    d = np.abs(x) % TWO_PI
    return np.minimum(d, TWO_PI - d)


def load_theta_91():
    """The recipe. Frozen in Lab 99's metrics; never re-tuned, never fitted here."""
    with open(M / "99_variational_floor" / "metrics_99.json", encoding="utf-8") as f:
        m99 = json.load(f)
    rec = [c for c in m99["stageB_classA"] if c["frame"] == FRAME][0]
    return np.array(rec["theta"], dtype=float)


# ============================================================ the machine ====

def instrumented_run(Qf, theta, FREQS, THETAS0, T):
    """Lab 100 v2's Model Two loop, instrumented.

    Identical arithmetic to lab100.run_model_two - the outcome stream is compared
    against it below, so any divergence is caught rather than assumed away.
    Records, per fold: the three arrow lengths seen, the winner, the generator read,
    the three re-prepared magnitudes, the immediate re-measurement, and the full
    rotor-pool trajectory.
    """
    m_g, s_g, m_1, s_1, m_2, s_2 = theta
    z = lab93.z0.copy()
    thetas = THETAS0.copy()

    arrows = np.empty((T, 3))
    winners = np.empty(T, dtype=np.int64)
    gens = np.empty(T, dtype=np.int64)
    mags = np.empty((T, 3))          # (g, c1, c2) as written by build_state_from_pool
    new_arrows = np.empty((T, 3))    # arrow lengths of the freshly written state
    repeat_same = np.zeros(T, dtype=bool)
    pool = np.empty((T, K, N_CHANNELS))

    for t in range(T):
        arrows[t] = [abs(np.vdot(Qf[:, k], z)) for k in range(3)]
        znorm = np.linalg.norm(z)
        overlaps = np.array([abs(np.vdot(Qf[:, k], z)) ** 2 for k in range(3)]) / znorm ** 2
        j = int(np.argmax(overlaps))
        winners[t] = j

        gen_idx = t % K
        gens[t] = gen_idx
        phases6 = thetas[gen_idx]

        v0, v1, v2 = (phases6 / TWO_PI)[:3]
        mags[t] = [max(0.0, m_g + s_g * (v0 - 0.5)),
                   max(0.0, m_1 + s_1 * (v1 - 0.5)),
                   max(0.0, m_2 + s_2 * (v2 - 0.5))]

        # THE FOLD - verbatim, from the mirrored lab module
        z_new = lab100.build_state_from_pool(theta, phases6, j, Qf)

        new_arrows[t] = [abs(np.vdot(Qf[:, k], z_new)) for k in range(3)]
        # re-measure immediately, BEFORE the substrate turn
        ov2 = np.array([abs(np.vdot(Qf[:, k], z_new)) ** 2 for k in range(3)])
        repeat_same[t] = int(np.argmax(ov2)) == j

        z = lab93.U_S @ z_new
        thetas = np.mod(thetas + FREQS, TWO_PI)
        pool[t] = thetas

    return dict(arrows=arrows, winners=winners, gens=gens, mags=mags,
                new_arrows=new_arrows, repeat_same=repeat_same, pool=pool)


def free_pool(FREQS, THETAS0, T):
    """The same rotor pool, ticking with NO folds ever happening."""
    thetas = THETAS0.copy()
    pool = np.empty((T, K, N_CHANNELS))
    for t in range(T):
        thetas = np.mod(thetas + FREQS, TWO_PI)
        pool[t] = thetas
    return pool


# ================================================================= checks ====

def check_1_pool(rep, FREQS, used):
    """96 rotors as 16 x 6; omega = 2*pi*frac(sqrt(n)), n distinct and square-free;
    no two rates rationally locked."""
    n_rotors = FREQS.size
    shape_ok = FREQS.shape == (K, N_CHANNELS) and n_rotors == 96 and len(used) == 96

    distinct = len(set(used)) == len(used)
    sf = [is_squarefree_int(n) for n in used]
    all_sf = all(sf)

    # omega = 2*pi*frac(sqrt(n)) for the integers actually accepted, in build order
    omega_expected = np.array([TWO_PI * (np.sqrt(float(n)) % 1.0) for n in used])
    omega_measured = FREQS.reshape(-1)
    omega_dev = float(np.max(np.abs(omega_measured - omega_expected)))

    # The generator the pool draws from: square-free integers in order. The article
    # names the ones it must skip: 4, 8, 9, 12.
    g = lab100.squarefree_gen()
    first12 = [next(g) for _ in range(12)]
    skips_ok = first12 == [2, 3, 5, 6, 7, 10, 11, 13, 14, 15, 17, 19]

    # No two rates rationally locked - EXACT, and at every order at once.
    # A lock means p*omega_i - q*omega_j = 0 (mod 2*pi) for integers p, q not both 0,
    # i.e. p*sqrt(n_i) - q*sqrt(n_j) is an integer m. Squaring:
    #   2*p*q*sqrt(n_i*n_j) = p^2*n_i + q^2*n_j - m^2  (an integer)
    # so a lock forces sqrt(n_i*n_j) rational, i.e. n_i*n_j a perfect square. For
    # distinct square-free integers it never is. Checked over all 4560 pairs.
    bad_pairs = [(a, b) for i, a in enumerate(used) for b in used[i + 1:]
                 if is_perfect_square(a * b)]
    # degenerate p-or-q-zero case: a lock would need n itself to be a perfect square
    bad_single = [n for n in used if is_perfect_square(n)]
    no_lock = not bad_pairs and not bad_single

    # supplementary numeric diagnostic (not the proof): how close does the pool get
    # to a low-order resonance anyway?
    om = omega_measured
    worst = np.inf
    for i in range(len(om)):
        for p in range(1, 9):
            d = circ(p * om[i] - np.arange(1, 9)[:, None] * om[i + 1:][None, :])
            if d.size:
                worst = min(worst, float(d.min()))

    ok = shape_ok and distinct and all_sf and omega_dev < 1e-12 and skips_ok and no_lock
    rep.add(1, "Pool structure: 96 rotors as 16 generators x 6 channels, rates "
               "omega = 2*pi*frac(sqrt(n)) over distinct square-free n, none rationally locked",
            [("pool shape",
              f"{FREQS.shape[0]} generators x {FREQS.shape[1]} channels = {n_rotors} rotors, "
              f"{len(used)} integers recorded",
              "16 x 6 = 96 rotors, 96 integers"),
             ("integers distinct",
              f"{len(set(used))} distinct of {len(used)}  (first: {used[:6]}, max: {max(used)})",
              "all 96 distinct"),
             ("every integer square-free",
              f"{sum(sf)}/96 square-free",
              "96/96"),
             ("rate law omega = 2*pi*frac(sqrt(n))",
              f"max |omega_measured - 2*pi*frac(sqrt(n))| = {omega_dev:.3e}",
              "< 1e-12"),
             ("candidate stream skips the squares (article names 4, 8, 9, 12)",
              f"first 12 candidates = {first12}",
              "[2, 3, 5, 6, 7, 10, 11, 13, 14, 15, 17, 19]"),
             ("no two rates rationally locked (exact test over all 4560 pairs: "
              "n_i*n_j is never a perfect square, so p*sqrt(n_i) - q*sqrt(n_j) is "
              "never an integer, at any order p, q)",
              f"{len(bad_pairs)} locked pairs, {len(bad_single)} self-locked rates",
              "0 and 0")],
            ok,
            notes=[f"supplementary (not the proof): closest low-order near-resonance "
                   f"over all pairs and p,q <= 8 is {worst:.3e} rad - small, never zero."])


def check_2_traced_fold(rep, run):
    """The article's worked example: the fold at tick t = 1000."""
    t = T_TRACE
    arrows = run["arrows"][t]
    winner = int(run["winners"][t])
    gen = int(run["gens"][t])
    mags = run["mags"][t]
    new_arrows = run["new_arrows"][t]

    exp_arrows = np.array([1.424979609, 0.377518968, 0.416932983])
    exp_mags = np.array([1.311574829, 0.927769907, 0.496544010])

    d_arrows = float(np.max(np.abs(arrows - exp_arrows)))
    d_mags = float(np.max(np.abs(mags - exp_mags)))
    d_state = float(np.max(np.abs(new_arrows - mags)))

    ok = (d_arrows < 1e-9 and winner == 0 and gen == 8 and d_mags < 1e-9
          and d_state < 1e-12 and gen == T_TRACE % K)

    rep.add(2, f"The traced fold at tick t = {T_TRACE} of the certified run",
            [("the three arrow lengths the observer compares",
              ", ".join(f"{x:.9f}" for x in arrows),
              "1.424979609, 0.377518968, 0.416932983"),
             ("the winner (index in code; 'the first one wins')",
              f"index {winner}",
              "index 0"),
             ("the generator read (1000 mod 16)",
              f"{gen}  ({T_TRACE} mod {K} = {T_TRACE % K})",
              "8"),
             ("the three re-prepared magnitudes (g, c1, c2)",
              ", ".join(f"{x:.9f}" for x in mags),
              "1.311574829, 0.927769907, 0.496544010"),
             ("'the arrows ARE the state': arrow lengths of the freshly written state",
              f"max |new arrow - written magnitude| = {d_state:.3e}",
              "< 1e-12 (identical)")],
            ok)


def check_3_pinned(rep, run):
    """Winner pinned, losers wander."""
    g, c1, c2 = run["mags"][:, 0], run["mags"][:, 1], run["mags"][:, 2]
    s_g = float(g.max() - g.min())
    s_1 = float(c1.max() - c1.min())
    s_2 = float(c2.max() - c2.min())
    ratio = min(s_1, s_2) / s_g

    ok = (len(g) >= 4000
          and 0.0060 <= s_g <= 0.0070
          and 0.09 <= c1.min() <= 0.12 and 0.95 <= c1.max() <= 0.99
          and 0.21 <= c2.min() <= 0.25 and 0.77 <= c2.max() <= 0.81
          and ratio > 50)

    rep.add(3, "Winner pinned, losers wander",
            [("folds measured", f"{len(g)}", ">= 4000"),
             ("winner amplitude: spread and centre",
              f"spread {s_g:.6f}  (range {g.min():.6f} .. {g.max():.6f})",
              "spread ~0.0065, essentially fixed near 1.3125"),
             ("loser 1 amplitude range",
              f"{c1.min():.4f} .. {c1.max():.4f}  (spread {s_1:.4f})",
              "roughly 0.10 .. 0.97"),
             ("loser 2 amplitude range",
              f"{c2.min():.4f} .. {c2.max():.4f}  (spread {s_2:.4f})",
              "roughly 0.23 .. 0.79"),
             ("wander ratio (smallest loser spread / winner spread)",
              f"{ratio:.1f}x   (loser 1: {s_1/s_g:.1f}x, loser 2: {s_2/s_g:.1f}x)",
              "> 50x - the winner is pinned, the losers roam")],
            ok)


def check_4_lean(rep, run, theta):
    """The lean. DEFINITION MATTERS - stated explicitly in the output."""
    g, c1, c2 = run["mags"][:, 0], run["mags"][:, 1], run["mags"][:, 2]
    lean_mean = g / (0.5 * (c1 + c2))
    lean_max = g / np.maximum(c1, c2)
    med = float(np.median(lean_mean))
    lo, hi = float(lean_mean.min()), float(lean_mean.max())
    med_max = float(np.median(lean_max))

    m_g, _, m_1, _, m_2, _ = theta
    band_centre = float(m_g / (0.5 * (m_1 + m_2)))

    ok = (2.49 <= med <= 2.52
          and abs(band_centre - 2.5057570976993087) < 1e-9
          and 1.45 <= lo <= 1.55 and 7.3 <= hi <= 7.8)

    rep.add(4, "The lean: the winner sits about two and a half times the losers",
            [("DEFINITION USED (load-bearing): lean = g / mean(c1, c2), per event",
              "g / (0.5 * (c1 + c2))",
              "the article's form - the mean, not the max"),
             ("median per-event lean",
              f"{med:.4f}",
              "~2.50"),
             ("band-centre ratio m_g / mean(m_1, m_2) of the frozen recipe",
              f"{band_centre:.10f}",
              "2.5057570976993087"),
             ("per-event range (this is a MEDIAN, not a constant)",
              f"{lo:.4f} .. {hi:.4f} over {len(g)} folds",
              "roughly 1.49 .. 7.56"),
             ("same data under the OTHER definition, for the avoidance of doubt",
              f"median of g / max(c1, c2) = {med_max:.4f}",
              "~1.99 - a different number for a different definition; "
              "the article's '2.5' is the mean form above")],
            ok)


def check_5_back_action(rep, run, FREQS, THETAS0):
    """Zero back-action: the pool's trajectory does not care whether folds happen."""
    pool_folded = run["pool"]
    pool_free = free_pool(FREQS, THETAS0, len(pool_folded))
    dev = float(np.max(np.abs(pool_folded - pool_free)))
    ok = dev == 0.0
    rep.add(5, "Zero back-action: the observer has no effect on the clockwork",
            [("max |rotor phase with folds - rotor phase with no folds| over "
              f"{len(pool_folded)} ticks x {K} generators x {N_CHANNELS} channels",
              f"{dev!r}",
              "0.0 exactly (bit-identical trajectory)")],
            ok)


def check_6_repeatability(rep, run):
    """Measure twice in a row, get the same answer."""
    same = run["repeat_same"]
    n = len(same)
    n_same = int(same.sum())
    ok = n >= 300 and n_same == n
    rep.add(6, "Repeatability: re-measure immediately (before the substrate turn) "
               "and the same arrow still wins",
            [("trials", f"{n}", ">= 300"),
             ("same winner on immediate re-measurement",
              f"{n_same}/{n}",
              f"{n}/{n} - the collapse postulate, never written down anywhere")],
            ok)


def check_7_fixed_point(rep, theta):
    """The derived ratio r*, and where the certified recipe sits relative to it."""
    p = M / "167_ratio_fixed_point" / "metrics_167b.json"
    with open(p, encoding="utf-8") as f:
        m167b = json.load(f)
    r_star = float(m167b["optimum"]["p_star"][0])
    r_star_err = float(m167b["optimum"]["p_star_err"][0])
    tol_r = float(m167b["slices"]["r"]["tol_loc"])
    verdict = m167b["verdict"]
    r_cert_stored = float(m167b["certified_point_position"]["r_cert"])

    # the certified recipe's ratio is recomputed LIVE from the frozen theta_91,
    # not read from lab 167b - it must agree with what 167b anchored against.
    m_g, _, m_1, _, m_2, _ = theta
    r_cert_live = float(m_g / (0.5 * (m_1 + m_2)))
    stored_agrees = abs(r_cert_live - r_cert_stored) < 1e-12
    gap = abs(r_cert_live - r_star)

    ok = (abs(r_star - 2.505144497539108) < 1e-9
          and stored_agrees
          and gap < 0.001
          and gap < tol_r
          and verdict == "DERIVED-MATCH")

    rep.add(7, "The derived ratio: the fixed point r* of the counting geometry, and "
               "the certified recipe sitting on it",
            [("r* (joint optimum in (r, s1, s2)) - READ from the frozen Lab 167b record",
              f"{r_star:.6f} +/- {r_star_err:.6f}",
              "2.505144 (article's 2.50514)"),
             ("the certified recipe's ratio - RECOMPUTED live from theta_91 "
              "(machine/99_variational_floor/metrics_99.json)",
              f"{r_cert_live:.6f}   (Lab 167b anchored against {r_cert_stored:.6f}; "
              f"agrees: {stored_agrees})",
              "2.505757"),
             ("gap between the optimizer's recipe and the derived fixed point",
              f"|{r_cert_live:.6f} - {r_star:.6f}| = {gap:.6f}",
              "~0.0006, and inside Lab 167b's declared r-axis location tolerance "
              f"{tol_r:.4f}"),
             ("Lab 167b verdict of record",
              verdict,
              "DERIVED-MATCH")],
            ok,
            notes=["HONEST SCOPE: item 7 is the only item on this page that is not "
                   "re-derived from scratch here. The r* derivation (Lab 167b) needs the "
                   "Lab 122 three-channel lift chain and ~7 minutes of certified "
                   "quadrature, which is out of scope for a mechanism pack. What runs "
                   "here reads the frozen metrics_167b.json, recomputes the certified "
                   "ratio live from theta_91, and checks the two against each other. "
                   "The derivation script (ratio_surface_167b.py) ships alongside for "
                   "line-by-line diffing against the research repo; to re-run it you "
                   "need the full lab tree.",
                   "The lean is therefore FORCED, not chosen - but the piece of that "
                   "argument you can execute here is the arithmetic, not the geometry."])


# =================================================================== main ====

def main():
    t0 = time.time()
    print("=" * 78)
    print("THE MACHINE - companion evidence pack (Quest for Entropy #2)")
    print("=" * 78)
    print("Scope: the MECHANISM. The twenty-question exam and the interference floor")
    print("       are episode 3's evidence and are deliberately not in this pack.")
    print()

    theta = load_theta_91()
    print(f"recipe theta_91 (frozen, from machine/99_variational_floor/metrics_99.json):")
    print(f"  m_g={theta[0]:.10f} s_g={theta[1]:.10f}")
    print(f"  m_1={theta[2]:.10f} s_1={theta[3]:.10f}")
    print(f"  m_2={theta[4]:.10f} s_2={theta[5]:.10f}")

    Qf = lab91.haar_frame(FRAME)
    print(f"\nframe: lab91.haar_frame({FRAME}) - chosen once, frozen, never re-tuned")

    print("building the rotor pool (square-free rates + near-resonance screen)...")
    FREQS, used = lab100.build_pool_v2()
    THETAS0 = lab100.build_thetas0(K)
    print(f"  {FREQS.size} rotors, {len(used)} square-free integers, max n = {max(used)}")

    print(f"\nrunning the machine for {T_FOLDS} folds...")
    run = instrumented_run(Qf, theta, FREQS, THETAS0, T_FOLDS)

    # The instrumented loop must BE the certified fold - not a lookalike.
    ref = lab100.run_model_two(Qf, theta, K, FREQS, THETAS0, T=T_FOLDS)
    identical = bool(np.array_equal(ref["outcomes"], run["winners"]))
    print(f"  instrumented loop vs lab100.run_model_two outcome stream: "
          f"{'IDENTICAL' if identical else 'DIVERGED'} over {T_FOLDS} folds")
    if not identical:
        sys.exit("FATAL: the instrumented loop diverged from the certified fold.")

    rep = Report()
    check_1_pool(rep, FREQS, used)
    check_2_traced_fold(rep, run)
    check_3_pinned(rep, run)
    check_4_lean(rep, run, theta)
    check_5_back_action(rep, run, FREQS, THETAS0)
    check_6_repeatability(rep, run)
    check_7_fixed_point(rep, theta)

    n_ok, n_total = rep.render()
    dt = time.time() - t0
    print("\n" + "=" * 78)
    if n_ok == n_total:
        print(f"ALL {n_total} MECHANISM CLAIMS REPRODUCED   ({dt:.1f}s)")
        print("=" * 78)
    else:
        print(f"{n_total - n_ok} of {n_total} CLAIMS FAILED TO REPRODUCE   ({dt:.1f}s)")
        print("Please report this - an issue with your platform and numpy version is")
        print("the perfect bug report.")
        print("=" * 78)
        sys.exit(1)


if __name__ == "__main__":
    main()
