"""Minimal PDAS ``bigtables.py`` v1.5 calculation snapshot.

This development-only file retains the upstream constants and calculation
functions needed to reproduce the Sentman atmosphere columns.  HTML generation,
unused transport properties, and the upstream unconditional ``main()`` call are
intentionally omitted.  The retained calculations are unchanged from:

https://www.pdas.com/packages/atmos.zip (file ``bigtables.py``)

Retrieved 2026-08-15.  The upstream program is public domain under the PDAS
legal statement at https://www.pdas.com/legal.html.  Exact archive and upstream
file SHA-256 values are recorded in ``docs/reference/us1976-data-provenance.md``.
"""

import math


PI = 3.14159265
REARTH = 6356.766
RSTAR = 8314.32
GZERO = 9.80665
MOLWT_ZERO = 28.9644
GMR = 1000 * GZERO * MOLWT_ZERO / RSTAR
TZERO = 288.15
ASOUNDZERO = 340.294
PART_SPEED_ZERO = math.sqrt((8.0 / PI) * RSTAR * TZERO / MOLWT_ZERO)


# The names and bodies below are retained from the PDAS source so that the
# generator can be audited directly against bigtables.py v1.5.
def EvaluateCubic(a, fa, fpa, b, fb, fpb, u):
    d = (fb - fa) / (b - a)
    t = (u - a) / (b - a)
    p = 1.0 - t
    fu = p * fa + t * fb - p * t * (b - a) * (p * (d - fpa) - t * (d - fpb))
    return fu


def KineticTemperature(z):
    C1 = -76.3232
    C2 = 19.9429
    C3 = 12.0
    C4 = 0.01875
    TC = 263.1905
    T7 = 186.8673
    Z8 = 91.0
    Z9 = 110.0
    T9 = 240.0
    Z10 = 120.0
    T10 = 360.0
    T12 = 1000.0

    if z <= Z8:
        t = T7
    elif z < Z9:
        xx = (z - Z8) / C2
        yy = math.sqrt(1.0 - xx * xx)
        t = TC + C1 * yy
    elif z <= Z10:
        t = T9 + C3 * (z - Z9)
    else:
        xx = (REARTH + Z10) / (REARTH + z)
        yy = (T12 - T10) * math.exp(-C4 * (z - Z10) * xx)
        t = T12 - yy

    return t


def LowerAtmosphere(alt):
    htab = [0.0, 11.0, 20.0, 32.0, 47.0, 51.0, 71.0, 84.852]
    ttab = [288.15, 216.65, 216.65, 228.65, 270.65, 270.65, 214.65, 186.946]
    ptab = [
        1.0,
        2.2336110e-1,
        5.4032950e-2,
        8.5666784e-3,
        1.0945601e-3,
        6.6063531e-4,
        3.9046834e-5,
        3.68501e-6,
    ]
    gtab = [-6.5, 0.0, 1.0, 2.8, 0, -2.8, -2.0, 0.0]

    h = alt * REARTH / (alt + REARTH)
    i = 0
    j = len(htab)
    while j > i + 1:
        k = (i + j) // 2
        if h < htab[k]:
            j = k
        else:
            i = k
    tgrad = gtab[i]
    tbase = ttab[i]
    deltah = h - htab[i]
    tlocal = tbase + tgrad * deltah
    theta = tlocal / ttab[0]

    if 0.0 == tgrad:
        delta = ptab[i] * math.exp(-GMR * deltah / tbase)
    else:
        delta = ptab[i] * math.pow(tbase / tlocal, GMR / tgrad)
    sigma = delta / theta
    return (sigma, delta, theta)


def MolecularWeight(altKm):
    Z = [
        86.0,
        93.0,
        100.0,
        107.0,
        114.0,
        121.0,
        128.0,
        135.0,
        142.0,
        150.0,
        160.0,
        170.0,
        180.0,
        190.0,
        200.0,
        220.0,
        260.0,
        300.0,
        400.0,
        500.0,
        600.0,
        700.0,
        800.0,
        900.0,
        1000.0,
    ]
    M = [
        28.95,
        28.82,
        28.40,
        27.64,
        26.79,
        26.12,
        25.58,
        25.09,
        24.62,
        24.10,
        23.49,
        22.90,
        22.34,
        21.81,
        21.30,
        20.37,
        18.85,
        17.73,
        15.98,
        14.33,
        11.51,
        8.00,
        5.54,
        4.40,
        3.94,
    ]
    MP = [
        -0.001340,
        -0.036993,
        -0.086401,
        -0.123115,
        -0.111136,
        -0.083767,
        -0.072368,
        -0.068190,
        -0.066300,
        -0.063131,
        -0.059786,
        -0.057724,
        -0.054318,
        -0.052004,
        -0.049665,
        -0.043499,
        -0.032674,
        -0.023804,
        -0.014188,
        -0.021444,
        -0.034136,
        -0.031911,
        -0.017321,
        -0.006804,
        -0.003463,
    ]

    if altKm <= 86.0:
        mw = MOLWT_ZERO
    elif altKm >= 1000.0:
        mw = M[24]
    else:
        i = 0
        j = len(Z) - 1
        while j > i + 1:
            k = (i + j) // 2
            if altKm < Z[k]:
                j = k
            else:
                i = k
            mw = EvaluateCubic(Z[i], M[i], MP[i], Z[i + 1], M[i + 1], MP[i + 1], altKm)

    return mw


__all__ = (
    "ASOUNDZERO",
    "KineticTemperature",
    "LowerAtmosphere",
    "MOLWT_ZERO",
    "MolecularWeight",
    "PART_SPEED_ZERO",
    "TZERO",
)
