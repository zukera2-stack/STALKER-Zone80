"""Ownership rules for the two synthetic sectors."""
from math import isfinite

BOUNDS = {"W": (400000, 400256), "E": (400256, 400512)}
BOTTOM = 5700000
TOP = BOTTOM + 256


def point_owner(x, y):
    if not (isfinite(x) and isfinite(y) and BOTTOM <= y <= TOP):
        return None
    for tile, (left, right) in BOUNDS.items():
        if left <= x < right or (tile == "E" and x == right):
            return tile
    return None


def assign_parts(features, tile):
    """Filter buffered points and reject empty or collapsed fixture geometries."""
    parts = {}
    for feature in features:
        source_id = feature["properties"]["source_id"]
        geometry = feature.get("geometry")
        if not geometry or not geometry.get("coordinates"):
            continue
        kind = geometry["type"]
        coords = geometry["coordinates"]
        if kind == "Point":
            if len(coords) != 2 or point_owner(*coords) != tile:
                continue
        elif kind == "LineString":
            if len({tuple(point) for point in coords}) < 2:
                continue
        elif kind == "Polygon":
            if len(coords) != 1:
                raise ValueError("Fixture polygons require one exterior ring")
            ring = coords[0]
            if len(ring) < 4 or ring[0] != ring[-1]:
                continue
            x0, y0 = ring[0]
            area2 = sum((a - x0) * (d - y0) - (b - y0) * (c - x0)
                        for (a, b), (c, d) in zip(ring, ring[1:]))
            if area2 == 0:
                continue
        else:
            raise ValueError(f"Unsupported fixture geometry: {kind}")
        if source_id in parts:
            raise ValueError(f"Duplicate source in tile {tile}: {source_id}")
        parts[source_id] = {**feature, "properties": {
            **feature["properties"], "part_id": f"{source_id}:{tile}"}}
    return [parts[source_id] for source_id in sorted(parts)]
