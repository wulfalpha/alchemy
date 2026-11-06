"""Material-efficiency awards for completed Adventure experiments.

Medals are presentation derived from saved material, not another ranking key.
Each experiment revision carries its own (silver, gold) thresholds (see
`adventure.Experiment.medals`). Keep a released revision's thresholds stable so
saved wins retain their displayed awards; change rules with a new revision.
"""
SILVER_MATERIAL = 30
GOLD_MATERIAL = 45
V1_THRESHOLDS = (SILVER_MATERIAL, GOLD_MATERIAL)   # revisions without unstable symbols
UNSTABLE_THRESHOLDS = (40, 50)                     # unstable symbols: calibrated 2026-11-05


def efficiency_medal(material_left, thresholds=V1_THRESHOLDS):
    """Grade a successful run; missing historical statistics have no award."""
    if material_left is None:
        return None
    silver, gold = thresholds
    if material_left >= gold:
        return 'Gold'
    if material_left >= silver:
        return 'Silver'
    return 'Bronze'
