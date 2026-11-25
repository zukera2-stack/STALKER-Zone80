using System.Security.Cryptography;
using System.Text;
using GameRealisticMap;
using GameRealisticMap.ElevationModel;
using GameRealisticMap.Geometries;
using GameRealisticMap.Osm;
using GameRealisticMap.Configuration;
using GameRealisticMap.Conditions;
using GameRealisticMap.ManMade;
using GameRealisticMap.ManMade.Places;
using GameRealisticMap.ManMade.Roads;
using GameRealisticMap.Nature.Ocean;
using Pmad.HugeImages.Storage;
using Zone80.GmBridge;

// Synthetic-only smoke test. No real files, no network, no layer invocation.
static string Sha(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
static void Check(bool x,string why){if(!x)throw new Exception(why);}
static async Task Reject(Func<Task> f,string why){try{await f();}catch(InvalidOperationException){return;}throw new Exception(why);}
var asc=Encoding.ASCII.GetBytes("ncols 3\nnrows 3\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n31 32 33\n21 22 23\n11 12 13\n");
var prj=Encoding.ASCII.GetBytes("synthetic test metadata (not a real CRS WKT)");
var c=new NodeContract(3,30,1000,2000,"EPSG:32636","EGM2008","m",Sha(asc),Sha(prj),"synthetic fixture only");
var data=NodeInput.Parse(asc,prj,c);
// Synthetic area verifies native grid indexing only, NOT real UTM alignment.
var area=TerrainAreaUTM.CreateFromCenter("0, 0",30f,3);
var catalog=new BuildersCatalog(new DefaultBuildersConfig(),DefaultSourceLocations.Instance);
GmSession Session()=>GmSession.CreateSynthetic(data,catalog,null!,area,new NoneOsmDataSource(),new MapProcessingOptions(),new MemoryHugeImageStorage());
using(var s=Session())
{
    s.SeedSynthetic(new CategoryAreaData(new List<CategoryArea>()));
    s.SeedSynthetic(new CitiesData(new List<City>()));
    s.SeedSynthetic(new OceanData(new List<TerrainPolygon>(),new List<TerrainPolygon>(),false));
    s.SeedSynthetic(new RoadsData(new List<Road>()));
    var result=await s.ProbeAsync(async ctx=>{
        var g=(await ctx.GetDataAsync<ElevationData>()).Elevation;
        Check(g[0,0]==11 && g[2,2]==33,"orientation");
        Check(g.ElevationAt(new TerrainPoint(30,0))==12,"node sample");
        // Use actual GRM condition consumer on the seeded synthetic support data.
        var evaluator=new ConditionEvaluator((IBuildContext)ctx);
        Check(evaluator.GetElevation(new TerrainPoint(30,0))==12,"condition sample");
        await Reject(async()=>{await ctx.GetDataAsync<RawElevationData>();},"raw fallback");
        await Reject(async()=>{await ctx.GetDataAsync<ElevationWithLakesData>();},"mutation builder fallback");
        return g[1,1];
    });
    Check(result==22,"sample");
}
using(var s=Session()) await Reject(async()=>{await s.ProbeAsync(async ctx=>{var g=(await ctx.GetDataAsync<ElevationData>()).Elevation;g[0,0]=999;return 0;});},"mutation not caught");
Console.WriteLine("SYNTHETIC GRM CORE SMOKE PASS "+data.Fingerprint);
