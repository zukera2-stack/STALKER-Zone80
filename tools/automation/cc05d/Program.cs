using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text;
using GameRealisticMap;
using GameRealisticMap.Arma3;
using GameRealisticMap.Arma3.Assets;
using GameRealisticMap.Arma3.TerrainBuilder;
using GameRealisticMap.Conditions;
using GameRealisticMap.Configuration;
using GameRealisticMap.ElevationModel;
using GameRealisticMap.Geometries;
using GameRealisticMap.ManMade;
using GameRealisticMap.ManMade.Buildings;
using GameRealisticMap.ManMade.Objects;
using GameRealisticMap.ManMade.Places;
using GameRealisticMap.ManMade.Roads;
using GameRealisticMap.Nature.Ocean;
using GameRealisticMap.Nature.Trees;
using GameRealisticMap.Osm;
using Pmad.HugeImages.Storage;
using Pmad.ProgressTracking;
using Zone80.GmBridge;

// Synthetic-only integration probe. No CLI real input, no actual P3D files or map output.
static string Sha(byte[] b) => Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
static void Check(bool ok,string reason) { if (!ok) throw new Exception(reason); }
static async Task Reject(Func<Task> action,string expected) {
    try { await action(); } catch(InvalidOperationException e) when(e.Message.Contains(expected)) { return; }
    throw new Exception("expected refusal: "+expected);
}
var cfg = new Arma3MapConfig(new Arma3MapConfigJson {Center="9 N, 33 E",GridSize=4,GridCellSize=30,WorldName="synthetic_only",TargetModDirectory="unused",TileSize=512});
var area=cfg.TerrainArea;
var points=new[]{new TerrainPoint(30,30),new TerrainPoint(60,60),new TerrainPoint(30,60)};
var xml="<osm version=\"0.6\">"+string.Join("",points.Select((p,i)=>{
    var c=area.TerrainPointToLatLng(p);
    return FormattableString.Invariant($"<node id=\"{i+1}\" lat=\"{c.Y:R}\" lon=\"{c.X:R}\"><tag k=\"natural\" v=\"tree\"/></node>");
}))+"</osm>";
var assets=new Arma3Assets { BaseWorldName="SYNTHETIC_ONLY",BaseDependency="SYNTHETIC_ONLY" };
var marker=new ModelInfo("synthetic_tree_not_a_file", "synthetic_only.p3d", Vector3.Zero);
assets.Objects[ObjectTypeId.Tree]=new List<ObjectDefinition>{new(new Composition(new CompositionObject(marker,Matrix4x4.Identity)),1,new PointCondition("Elevation > 25"))};
var generator=new Arma3LayerGeneratorCatalog(assets).Generators.Single(g=>g.GetType().Name=="TreesGenerator");
async Task<string[]> Run(int delta,int expected) {
    string row=string.Join(" ",new[]{10,20,40,50}.Select(x=>(x+delta).ToString(CultureInfo.InvariantCulture)));
    var asc=Encoding.ASCII.GetBytes("ncols 4\nnrows 4\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n"+string.Concat(Enumerable.Repeat(row+"\n",4)));
    var prj=Encoding.ASCII.GetBytes("synthetic not a real WKT");
    var input=NodeInput.Parse(asc,prj,new NodeContract(4,30,1000,2000,"EPSG:32636","EGM2008","m",Sha(asc),Sha(prj),"synthetic fixture only"));
    // Dummy projected coordinates are not a real CRS/area equivalence proof.
    var grid=input.CopyGrid();
    var catalog=new GuardedCatalog(new BuildersCatalog(new DefaultBuildersConfig(),DefaultSourceLocations.Instance),new[]{typeof(ConditionEvaluator),typeof(TreesData)});
    var ctx=new BuildContext(catalog,new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),cfg,new MemoryHugeImageStorage());
    try {
        ctx.SetData(new ElevationData(grid));
        ctx.SetData(new CategoryAreaData(new List<CategoryArea>()));
        ctx.SetData(new CitiesData(new List<City>()));
        ctx.SetData(new OceanData(new List<TerrainPolygon>(),new List<TerrainPolygon>(),false));
        ctx.SetData(new RoadsData(new List<Road>()));
        ctx.SetData(new BuildingsData(new List<Building>()));
        await Reject(async()=>{await ctx.GetDataAsync<RawElevationData>();},"Unreviewed builder");
        await Reject(async()=>{await ctx.GetDataAsync<ElevationWithLakesData>();},"Unreviewed builder");
        await Reject(async()=>{await ctx.GetDataAsync<ElevationOutOfBoundsData>();},"Unreviewed builder");
        var generated=(await generator.Generate(cfg,ctx,new NoProgress())).ToList();
        var trees=await ctx.GetDataAsync<TreesData>();
        Console.WriteLine("debug OSM nodes="+ctx.OsmSource.Nodes.Count()+" tree points="+string.Join(";",trees.Points.Select(p=>p.Vector.ToString())));
        Check(trees.Points.Count==3,"actual OSM TreesBuilder must produce three points");
        foreach(var p in points) Check(trees.Points.Any(t=>Vector2.Distance(p.Vector,t.Vector)<0.2f),"OSM roundtrip");
        Check(generated.Count==expected,"count expected "+expected+" got "+generated.Count);
        var evaluator=await ctx.GetDataAsync<ConditionEvaluator>();
        foreach(var o in generated) {
            Check(o.IsValid && o.Model.Name==marker.Name && o.ElevationMode==ElevationMode.Relative,"record");
            Check(evaluator.GetElevation(o.Point)>25,"height rule");
            Check(Math.Abs(o.ToWrpTransform(grid).M42-evaluator.GetElevation(o.Point))<0.01f,"relative Z matrix");
        }
        Check(NodeInput.GridHash(grid)==input.Fingerprint,"mutation");
        var records=generated.Select(o=>o.ToTerrainBuilderCSV()).OrderBy(x=>x,StringComparer.Ordinal).ToArray();
        Console.WriteLine($"delta={delta} source_points={trees.Points.Count} selected={generated.Count} grid={input.Fingerprint} records_sha={Sha(Encoding.UTF8.GetBytes(string.Join("\n",records)))}");
        return records;
    } finally {ctx.DisposeHugeImages();}
}
var mixed=await Run(0,1);var repeated=await Run(0,1);Check(mixed.SequenceEqual(repeated),"nondeterministic records");
await Run(-100,0);await Run(100,3);
Console.WriteLine("SYNTHETIC GRM ARMA3 TREES PASS: native OSM builder, height filter, relative Z, deterministic, immutable grid, blocked fallback");
