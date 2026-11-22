import json, os, pathlib
r=pathlib.Path(os.environ['GIS_TILE_ROOT'])
x,y=400000,5700000
def feature(id,t,coords):
    return {'type':'Feature','properties':{'source_id':id},'geometry':{'type':t,'coordinates':coords}}
fs=[feature('W','Point',[x+32,y+40]),feature('E','Point',[x+480,y+40]),feature('S','Point',[x+256,y+44]),feature('R','LineString',[[x+180,y+64],[x+320,y+64]]),feature('B','Polygon',[[[x+220,y+100],[x+300,y+100],[x+300,y+140],[x+220,y+140],[x+220,y+100]]])]
def geo(path,features):
    path.write_text(json.dumps({'type':'FeatureCollection','crs':{'type':'name','properties':{'name':'EPSG:32636'}},'features':features}))
geo(r/'features.geojson',fs)
for tile,dx in [('W',0),('E',256)]:
    d=r/tile; d.mkdir()
    left=x+dx; right=left+256
    rows=[[(-9999 if (row==4 and col in (0,31)) else 100+row*2+abs((dx//8+col)-31.5)*0.5) for col in range(32)] for row in range(32)]
    (d/'dem.asc').write_text(f'ncols 32\nnrows 32\nxllcorner {left}\nyllcorner {y}\ncellsize 8\nNODATA_value -9999\n'+'\n'.join(' '.join(map(str,row)) for row in rows))
    crop=feature(tile,'Polygon',[[[left,y],[right,y],[right,y+256],[left,y+256],[left,y]]])
    geo(d/'crop.geojson',[crop])
    (d/'tile.gms').write_text('''GLOBAL_MAPPER_SCRIPT VERSION=1.00
SET_LOG_FILE FILENAME="batch.log" 
LOAD_PROJECTION PROJ_EPSG_CODE=32636
IMPORT FILENAME="dem.asc" TYPE=ARCASCIIGRID PROJ="EPSG:32636"
EXPORT_ELEVATION FILENAME="out.tif" TYPE=GEOTIFF SAMPLE_TYPE=F32 ELEV_UNITS=METERS SPATIAL_RES=8,8 FILL_GAPS=NO
EXPORT_ELEVATION FILENAME="out.asc" TYPE=ARCASCIIGRID ELEV_UNITS=METERS SPATIAL_RES=8,8 FILL_GAPS=NO
IMPORT FILENAME="../features.geojson" PROJ="EPSG:32636"
EXPORT_VECTOR FILENAME="out.geojson" TYPE=GEOJSON POLYGON_CROP_FILE="crop.geojson" POLYGON_CROP_FILE_PROJ="EPSG:32636"
LOG_MESSAGE "GIS04_COMPLETE"
''')
