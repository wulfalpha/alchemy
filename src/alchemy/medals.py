"""Material-efficiency awards for completed Adventure experiments.

Medals are presentation derived from saved material, not another ranking key.
Keep these v1 thresholds stable so saved wins retain their displayed awards.
"""
SILVER_MATERIAL = 30
GOLD_MATERIAL = 45


def efficiency_medal(material_left):
    """Grade a successful run; missing historical statistics have no award."""
    if material_left is None:
        return None
    if material_left >= GOLD_MATERIAL:
        return 'Gold'
    if material_left >= SILVER_MATERIAL:
        return 'Silver'
    return 'Bronze'
