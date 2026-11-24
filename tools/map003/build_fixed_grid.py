#!/usr/bin/env python3
"""MAP-003: fixed 64x64 x 30m terrain pilot, grid FIRST, Copernicus pixels SECOND.

On a small GitHub hosted job, read only the needed source COG via HTTP ranges.
No extrapolation, no synthetic height fill, no terrain or object placement.
Created files are short-lived workflow artifacts, not Git commits.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

# Deterministic pilot grid, centred on the verified MAP-002 60x62 export.
CRS = "EPSG:32636"
WIDTH = HEIGHT = 64
CELL_M = 30.0
XLL_M = 294373.084  # 60m W of MAP-002 corner
YLL_M = 5698122.108  # 30m S of MAP-002 corner
WEST, SOUTH, EAST, NORTH = 30.045, 51.398, 30.070, 51.414
DSM_TILE = "Copernicus_DSM_COG_10_N51_00_E030_00_DEM"
SOURCE = (
    "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
    f"{DSM_TILE}/{DSM_TILE}.tif"
)
NODATA = -9999.0


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest().upper()


def grid() -> dict:
    """Independent of GDAL or rasterio; immutable pilot grid contract."""
    x_max = XLL_M + WIDTH * CELL_M
    y_max = YLL_M + HEIGHT * CELL_M
    return {
        "crs": CRS, "ncols": WIDTH, "nrows": HEIGHT, "cellsize_m": CELL_M,
        "xllcorner": XLL_M, "yllcorner": YLL_M,
        "bounds_utm36": [XLL_M, YLL_M, x_max, y_max],
        "input_bbox_wgs84": [WEST, SOUTH, EAST, NORTH],
        "pixel_interpretation": "area; ASC center of (row,col) at xll+(col+.5)*cell, ytop-(row+.5)*cell",
        "verticalDatum": "EGM2008 as documented for Copernicus GLO-30; no vertical transformation",
        "type": "DSM (may contain structures/vegetation, NOT historical bare-earth)",
    }


def verify_geo_coverage() -> dict:
    """Check that all four original WGS84 bbox corners fit target 64x64 grid."""
    from rasterio.warp import transform
    lon = [WEST, WEST, EAST, EAST]
    lat = [SOUTH, NORTH, SOUTH, NORTH]
    east, north = transform("EPSG:4326", CRS, lon, lat)
    x1, y1, x2, y2 = grid()["bounds_utm36"]
    margins = [min(east)-x1, x2-max(east), min(north)-y1, y2-max(north)]
    if min(margins) < 0:
        raise ValueError(f"Grid does not fully cover source AOI bbox, margin={margins}")
    return {"cornerEastings_m": east, "cornerNorthings_m": north, "minGridMargins_m": margins}


def write_arc_ascii(path: Path, data) -> None:
    # Explicit row order: north-to-south; first row is max northing.
    with path.open("x", encoding="ascii", newline="\n") as f:
        f.write(f"ncols {WIDTH}\n")
        f.write(f"nrows {HEIGHT}\n")
        f.write(f"xllcorner {XLL_M:.3f}\n")
        f.write(f"yllcorner {YLL_M:.3f}\n")
        f.write(f"cellsize {CELL_M:.0f}\n")
        f.write(f"NODATA_value {NODATA:.0f}\n")
        for row in data:
            f.write(" ".join(f"{float(v):.6f}" for v in row) + "\n")


def sample_points(data) -> list[dict]:
    import rasterio.warp
    # Row 0 is North. Five distinct interior, one near each quadrant + centre.
    locations = [(4, 4), (4, 59), (32, 32), (59, 4), (59, 59)]
    out = []
    for row, col in locations:
        x = XLL_M + (col + 0.5)*CELL_M
        y = YLL_M + (HEIGHT - row - 0.5)*CELL_M
        lon, lat = rasterio.warp.transform(CRS, "EPSG:4326", [x], [y])
        out.append({
            "rowNorthFirst": row, "colWestFirst": col,
            "easting_m": round(x, 3), "northing_m": round(y, 3),
            "lon": round(lon[0], 8), "lat": round(lat[0], 8),
            "DSM_height_m": round(float(data[row, col]), 5),
        })
    return out


def build(out: Path) -> int:
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import Affine
    from rasterio.vrt import WarpedVRT

    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"Refusing to overwrite existing data: {out}")
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "stage": "MAP-003", "status": "RUNNING",
        "createdUTC": utc(), "target": grid(), "source": SOURCE,
        "sourceLicense": "Copernicus DEM GLO-30 Public 2021; attribution required",
        "purpose": "terrain-only test; no buildings/Arma objects",
        "globalMapperExecutedHere": False, "terrainBuilderExecutedHere": False,
        "resampling": "bilinear from original COG, not from the old 60x62 crop",
        "noArtificialFill": True,
    }
    state_path = out / "GRID_MANIFEST.json"
    state_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    try:
        manifest["coverage"] = verify_geo_coverage()
        dst_transform = Affine(CELL_M, 0, XLL_M, 0, -CELL_M, YLL_M + HEIGHT*CELL_M)
        # Source is native WGS84 GLO-30 COG. The VRT reads only the minimal
        # source blocks relevant to this small target grid over HTTP range.
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
            GDAL_HTTP_TIMEOUT="30", GDAL_HTTP_MAX_RETRY="0",
        ):
            with rasterio.open(SOURCE) as src:
                if src.crs is None or src.crs.to_epsg() != 4326:
                    raise ValueError(f"Unexpected source CRS {src.crs}")
                with WarpedVRT(
                    src,
                    crs=CRS, transform=dst_transform, width=WIDTH, height=HEIGHT,
                    resampling=Resampling.bilinear,
                    src_nodata=src.nodata, nodata=NODATA,
                ) as vrt:
                    band = vrt.read(1, masked=True)
        valid = band.compressed()
        missing = int(np.ma.getmaskarray(band).sum())
        if not len(valid) or not np.isfinite(valid).all():
            raise ValueError("No valid heights or nonfinite DSM source values")
        manifest["sourceCoverage"] = {
            "totalCells": WIDTH*HEIGHT,
            "validCells": int(len(valid)), "noDataCells": missing,
            "heightMin_m": round(float(valid.min()), 6),
            "heightMax_m": round(float(valid.max()), 6),
        }
        if missing:
            raise ValueError(f"STOP: {missing} actual NoData cells. Do not invent/interpolate missing terrain")

        data = band.filled(NODATA).astype(np.float32)
        asc = out / "pilot-tb-64x64.asc"
        tif = out / "pilot-tb-64x64.tif"
        write_arc_ascii(asc, data)
        with rasterio.open(
            tif, "w", driver="GTiff", width=WIDTH, height=HEIGHT, count=1,
            dtype="float32", crs=CRS, transform=dst_transform,
            nodata=NODATA, compress="deflate", predictor=3,
        ) as dst:
            dst.write(data, 1)
        # Open both source-independent outputs and verify the same actual grid.
        with rasterio.open(tif) as src:
            actual = src.read(1)
            if src.width != WIDTH or src.height != HEIGHT or src.crs.to_epsg() != 32636:
                raise ValueError("Incorrect output GeoTIFF dimensions/CRS")
            if not np.allclose(actual, data, rtol=0, atol=1e-5):
                raise ValueError("GeoTIFF sample mismatch")
        raw_lines = asc.read_text(encoding="ascii").splitlines()
        if len(raw_lines) != 6+HEIGHT:
            raise ValueError("Incorrect ASCII row count")
        rows = np.array([
            [float(v) for v in line.split()] for line in raw_lines[6:]
        ], dtype=np.float32)
        if rows.shape != (HEIGHT,WIDTH) or not np.allclose(rows,data,rtol=0,atol=1e-4):
            raise ValueError("ASC/GeoTIFF height mismatch")
        manifest["fiveControlPoints"] = sample_points(data)
        manifest["outputs"] = {
            "asc": {"name": asc.name, "sha256":sha256(asc), "bytes":asc.stat().st_size},
            "geotiff": {"name":tif.name, "sha256":sha256(tif), "bytes":tif.stat().st_size},
        }
        manifest["status"] = "GRID_64_PASS_NEEDS_LOCAL_GM_TB_REVIEW"
        print(f"MAP-003 PASS 64x64; NoData=0; {manifest['outputs']}",flush=True)
        return 0
    except Exception as exc:
        manifest["status"] = "BLOCKED_NO_OUTPUT_VERIFIED"
        manifest["stopReason"] = f"{type(exc).__name__}: {exc}"
        print("MAP-003 BLOCKED:",manifest["stopReason"],file=sys.stderr,flush=True)
        return 2
    finally:
        manifest["finishedUTC"] = utc()
        state_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    sys.exit(build(Path(sys.argv[1] if len(sys.argv)>1 else "reports/MAP-003/artifact")))
