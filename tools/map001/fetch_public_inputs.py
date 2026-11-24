#!/usr/bin/env python3
"""MAP-001: bounded public-data retrieval for a GitHub Actions artifact.

No Google imagery. No OS/system modifications. No data is committed to Git.
The raw OSM XML and clipped Copernicus DSM are inputs for Global Mapper 26.2.
All outputs are in one dedicated artifact directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

WEST, SOUTH, EAST, NORTH = 30.045, 51.398, 30.070, 51.414
BBOX = (WEST, SOUTH, EAST, NORTH)
MAX_OSM_BYTES = 5 * 1024 * 1024
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
OSM_URL = (
    "https://api.openstreetmap.org/api/0.6/map?"
    "bbox=30.045,51.398,30.070,51.414"
)
DSM_TILE = "Copernicus_DSM_COG_10_N51_00_E030_00_DEM"
DSM_URL = (
    "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
    f"{DSM_TILE}/{DSM_TILE}.tif"
)
USER_AGENT = (
    "STALKER-Zone80-MAP001-small-extract/1.0 "
    "(+https://github.com/zukera2-stack/STALKER-Zone80)"
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def store_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_osm(out: Path) -> dict:
    """Single bounded request; stop on errors, no bulk download or retries."""
    req = urllib.request.Request(
        OSM_URL, headers={"User-Agent": USER_AGENT, "Accept": "application/xml"}
    )
    with urllib.request.urlopen(req, timeout=35) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"OSM HTTP {status}")
        length = response.headers.get("Content-Length")
        if length is not None and int(length) > MAX_OSM_BYTES:
            raise RuntimeError(f"OSM response too large: {length}")
        data = response.read(MAX_OSM_BYTES + 1)
    if len(data) > MAX_OSM_BYTES:
        raise RuntimeError("OSM response exceeded 5 MiB")
    root = ET.fromstring(data)
    if root.tag != "osm":
        raise RuntimeError("OSM response is not <osm>")
    raw = out / "pripyat_bbox.osm"
    raw.write_bytes(data)
    if not raw.is_file() or raw.stat().st_size < 100:
        raise RuntimeError("OSM XML empty")
    vectors = derive_way_vectors(root, out)
    return {
        "source": OSM_URL,
        "sourceDataset": "OpenStreetMap API 0.6",
        "license": "ODbL 1.0; © OpenStreetMap contributors",
        "retrievedUTC": utc(),
        "osmBytes": raw.stat().st_size,
        "osmSha256": sha256(raw),
        **vectors,
    }


def derive_way_vectors(root: ET.Element, out: Path) -> dict:
    """Conservative way-only derivation. Multipolygon relations stay unresolved.

    This is a preliminary catalog, not an assertion that every OSM building
    footprint has been recovered; see relation count in the manifest.
    """
    from shapely.geometry import LineString, Polygon, box, mapping
    from shapely.geometry.base import BaseGeometry

    aoi = box(WEST, SOUTH, EAST, NORTH)
    nodes = {}
    for n in root.findall("node"):
        try:
            nodes[n.attrib["id"]] = (float(n.attrib["lon"]), float(n.attrib["lat"]))
        except (KeyError, ValueError):
            continue

    roads, buildings = [], []
    missing_node_ways = 0
    rejected_invalid = 0
    for w in root.findall("way"):
        tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
        is_road = bool(tags.get("highway"))
        is_building = bool(tags.get("building"))
        if not (is_road or is_building):
            continue
        ref_ids = [n.get("ref") for n in w.findall("nd")]
        if any(ref not in nodes for ref in ref_ids):
            missing_node_ways += 1
            continue
        points = [nodes[ref] for ref in ref_ids]
        if len(points) < 2:
            rejected_invalid += 1
            continue
        if is_road:
            try:
                geom: BaseGeometry = LineString(points).intersection(aoi)
                if not geom.is_empty and geom.geom_type in ("LineString", "MultiLineString"):
                    roads.append(feature(geom, "way/" + w.attrib["id"], tags))
            except (ValueError, TypeError):
                rejected_invalid += 1
        if is_building:
            # Never invent missing closure or fabricate a polygon.
            if len(points) < 4 or points[0] != points[-1]:
                rejected_invalid += 1
                continue
            try:
                polygon: BaseGeometry = Polygon(points)
                if polygon.is_valid:
                    geom = polygon.intersection(aoi)
                    if not geom.is_empty and geom.geom_type in ("Polygon", "MultiPolygon"):
                        buildings.append(feature(geom, "way/" + w.attrib["id"], tags))
                else:
                    rejected_invalid += 1
            except (ValueError, TypeError):
                rejected_invalid += 1

    # Relations must be reconstructed separately, not silently counted as ways.
    rels = [
        rel.attrib.get("id") for rel in root.findall("relation")
        if any(t.get("k") == "building" or
               (t.get("k") == "type" and t.get("v") == "multipolygon")
               for t in rel.findall("tag"))
    ]
    for filename, features in [
        ("roads.geojson", roads),
        ("building_footprints.geojson", buildings),
    ]:
        store_json(out / filename, {
            "type": "FeatureCollection",
            "features": features,
        })
    return {
        "roadsWayCount": len(roads),
        "buildingsWayCount": len(buildings),
        "unresolvedRelationCount": len(rels),
        "missingNodeWayCount": missing_node_ways,
        "invalidGeometryCount": rejected_invalid,
        "geometryStatus": "PARTIAL_RELATIONS_NOT_ASSEMBLED",
        "outputRoadsSha256": sha256(out / "roads.geojson"),
        "outputBuildingsSha256": sha256(out / "building_footprints.geojson"),
    }


def feature(geometry, source_id: str, tags: dict) -> dict:
    from shapely.geometry import mapping

    return {
        "type": "Feature",
        "geometry": mapping(geometry),
        "properties": {
            "source_id": source_id,
            "source_dataset": "OpenStreetMap",
            "license": "ODbL 1.0",
            "historical_state": "unknown",
            "tags": tags,
        },
    }


def fetch_dem(out: Path) -> dict:
    """Read only the small AOI via HTTP-range COG windows using rasterio."""
    import numpy as np
    import rasterio
    from rasterio.windows import from_bounds, transform as window_transform

    # Explicit GDAL timeouts. No arbitrary AWS S3 key discovery or bulk tile dump.
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        GDAL_HTTP_TIMEOUT="30",
        GDAL_HTTP_MAX_RETRY="0",
    ):
        with rasterio.open(DSM_URL) as src:
            if src.crs is None:
                raise RuntimeError("DEM CRS missing")
            if src.crs.to_epsg() != 4326:
                raise RuntimeError(f"Unexpected Copernicus CRS: {src.crs}")
            win = from_bounds(*BBOX, transform=src.transform)
            win = win.round_offsets().round_lengths()
            if win.width < 2 or win.height < 2 or win.width * win.height > 250000:
                raise RuntimeError(f"Unexpected DEM window {win}")
            band = src.read(1, window=win, masked=True)
            if band.count() == 0:
                raise RuntimeError("Copernicus DSM AOI is all NoData")
            if band.dtype not in (np.dtype("float32"), np.dtype("float64")):
                raise RuntimeError(f"Unexpected DSM sample type {band.dtype}")
            transform = window_transform(win, src.transform)
            profile = {
                "driver": "GTiff",
                "height": int(win.height),
                "width": int(win.width),
                "count": 1,
                "dtype": "float32",
                "crs": src.crs,
                "transform": transform,
                "compress": "deflate",
                "predictor": 3,
                "nodata": -9999.0,
            }
            path = out / "pripyat_dem_copernicus_dsm30m.tif"
            with rasterio.open(path, "w", **profile) as dst:
                dst.write(band.filled(-9999).astype("float32"), 1)
            if path.stat().st_size > MAX_OUTPUT_BYTES:
                path.unlink()
                raise RuntimeError("DSM crop exceeds 64 MiB")
            heights = band.compressed()
            if not np.isfinite(heights).all():
                raise RuntimeError("Non-finite DSM samples")
            return {
                "source": DSM_URL,
                "sourceDataset": "Copernicus DEM GLO-30 Public 2021 (DSM, not bare-earth DEM)",
                "license": "Copernicus DEM GLO-30 Public attribution required; verify reuse terms",
                "retrievedUTC": utc(),
                "crs": str(src.crs),
                "verticalDatum": "EGM2008 (published source nominal; verify official metadata)",
                "width": int(win.width),
                "height": int(win.height),
                "transform": list(transform)[:6],
                "noData": -9999.0,
                "heightMin": float(heights.min()),
                "heightMax": float(heights.max()),
                "outputBytes": path.stat().st_size,
                "outputSha256": sha256(path),
            }


def run(out: Path) -> int:
    out = out.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("Refusing occupied output directory")
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "stage": "MAP-001",
        "status": "PARTIAL",
        "createdUTC": utc(),
        "bboxWgs84": list(BBOX),
        "buildingsPlaced": False,
        "globalMapperExecuted": False,
        "notes": "Downloaded as ephemeral workflow artifact, never committed to Git",
        "sources": {},
    }
    for key, fn in [("osm", fetch_osm), ("copernicusDSM", fetch_dem)]:
        try:
            manifest["sources"][key] = {"status": "PASS", **fn(out)}
        except Exception as exc:
            manifest["sources"][key] = {
                "status": "BLOCKED", "errorType": type(exc).__name__,
                "message": str(exc)[:800], "checkedUTC": utc(),
            }
    good = sum(v["status"] == "PASS" for v in manifest["sources"].values())
    manifest["status"] = "DOWNLOADED_NEEDS_GIS_QC" if good == 2 else "PARTIAL" if good else "BLOCKED"
    store_json(out / "SOURCE_MANIFEST.json", manifest)
    (out / "LICENSE_AND_USAGE.txt").write_text(
        "OSM features: © OpenStreetMap contributors, ODbL 1.0; "
        "https://www.openstreetmap.org/copyright\n"
        "Copernicus DEM GLO-30 Public: credits and redistribution terms "
        "at https://registry.opendata.aws/copernicus-dem/\n"
        "DSM includes vegetation and buildings, not surveyed bare-earth.\n"
        "WGS84 GIS vectors are current mapping, not verified 1986 objects.\n"
        "Do not publish Google Street View frames, PBO or P3D assets.\n"
        "All downloaded files are project inputs, not finished map products.\n",
        encoding="utf-8"
    )
    print(json.dumps({"status": manifest["status"], "sources": manifest["sources"]}, indent=2))
    return 0 if good == 2 else 1


if __name__ == "__main__":
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "reports/MAP-001/artifact")
    sys.exit(run(output))
