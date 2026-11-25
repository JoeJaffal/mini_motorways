"""Optional upgrade rule for the restricted roads/bridges/lights agent."""

def supported_mask(mask, offers):
    """Filter unsupported extras only with a supported, no-fewer-roads alternative.

    This is a heuristic, not true dominance: inventory and future offer weights
    can change. Never alter non-upgrade actions or filter both upgrade offers.
    """
    result = mask.copy()
    supported = {0, 1, 3}  # roads, bridges, lights in this restricted signal agent
    for i, offer in enumerate(offers[:2]):
        if offer['type'] in supported or not mask[i+1]:
            continue
        if any(j != i and mask[j+1] and other['type'] in supported
               and other['amount'] > 0 and other['roads'] >= offer['roads']
               for j, other in enumerate(offers[:2])):
            result[i+1] = False
    return result

