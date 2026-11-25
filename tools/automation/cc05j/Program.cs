using GameRealisticMap.Nature.Scrubs;
using GameRealisticMap.Nature.Forests;
using GameRealisticMap.Nature.Lakes;
using GameRealisticMap.ManMade.Railways;
using GameRealisticMap.ManMade.Cutlines;
using GameRealisticMap.Arma3.Assets.Filling;
using System.Numerics;
using System.Text;
using GameRealisticMap;
using GameRealisticMap.Arma3;
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
using System.Diagnostics.CodeAnalysis;
using System.Security.Cryptography;
using System.Text.Json;
using GameRealisticMap.Arma3.Assets;
using GameRealisticMap.Arma3.TerrainBuilder;

// Synthetic-only native layer test with actual pinned config and cache. No output files or real OSM.
static void Check(bool ok,string message) { if(!ok) throw new InvalidDataException(message); }
static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
static IEnumerable<string> Paths(JsonElement e) {
 if(e.ValueKind==JsonValueKind.String && e.GetString()!.EndsWith(".p3d",StringComparison.OrdinalIgnoreCase)) yield return e.GetString()!;
 else if(e.ValueKind==JsonValueKind.Array) { foreach(var a in e.EnumerateArray()) foreach(var p in Paths(a)) yield return p; }
 else if(e.ValueKind==JsonValueKind.Object) { foreach(var a in e.EnumerateObject()) foreach(var p in Paths(a.Value)) yield return p; }
}
try {
 Check(args.Length==2,"Expected v03 and modelinfo paths");
 var config=File.ReadAllBytes(args[0]); var cache=File.ReadAllBytes(args[1]);
 Check(Hash(config)=="418a6b1db5493c8b9f89f288024a769522f568483a5e614383d934506e7a941e","config hash");
 Check(Hash(cache)=="1177ec6d4618f198bd40f79880d3434ecbd7e0b8414881e23159c3e2a4cd9e94","cache hash");
 using var json=JsonDocument.Parse(cache); using var cfg=JsonDocument.Parse(config);
 var names=new HashSet<string>(StringComparer.OrdinalIgnoreCase);var paths=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
 foreach(var e in json.RootElement.EnumerateArray()) {
  Check(e.EnumerateObject().Select(p=>p.Name).OrderBy(s=>s,StringComparer.Ordinal).SequenceEqual(new[]{"BoundingCenter","Name","Path"}),"record shape");
  var name=e.GetProperty("Name").GetString();var path=e.GetProperty("Path").GetString();
  Check(!string.IsNullOrWhiteSpace(name)&&names.Add(name),"duplicate/blank name");
  Check(!string.IsNullOrWhiteSpace(path)&&paths.Add(path)&&path.EndsWith(".p3d",StringComparison.OrdinalIgnoreCase)&&!path.Contains('/')&&!path.Contains(':')&&path.Split('\\').All(s=>s.Length>0&&s!=".."&&s!="."),"invalid/duplicate path");
  var v=e.GetProperty("BoundingCenter");Check(v.GetArrayLength()==3&&v.EnumerateArray().All(n=>n.TryGetSingle(out float f)&&float.IsFinite(f)),"invalid vector");
 }
 var all=JsonSerializer.Deserialize<List<ModelInfo>>(cache)??throw new InvalidDataException("null cache");
 Check(all.Count==491&&paths.Count==491&&names.Count==491,"cache count");
 var requested=Paths(cfg.RootElement).ToHashSet(StringComparer.OrdinalIgnoreCase);
 Check(requested.Count==163&&requested.All(p=>p.StartsWith("a3\\",StringComparison.OrdinalIgnoreCase)),"config path scope");
 var selected=all.Where(m=>requested.Contains(m.Path)).ToArray();Check(selected.Length==163,"coverage");
 var resolver=new ReviewModels(selected);
 var assets=JsonSerializer.Deserialize<Arma3Assets>(config,Arma3Assets.CreateJsonSerializerOptions(resolver,false))??throw new InvalidDataException("null assets");
 Check(resolver.Seen.SetEquals(requested),"native parser lookup coverage");
 Check(assets.Materials.Definitions.Count==11&&assets.Roads.Count==9,"config parse shape");

 var map=new Arma3MapConfig(new Arma3MapConfigJson {Center="9 N, 33 E",GridSize=16,GridCellSize=30,WorldName="synthetic_only",TargetModDirectory="unused",TileSize=512});
 var area=map.TerrainArea;
 var generators=new Arma3LayerGeneratorCatalog(assets).Generators.Where(g=>new[]{"ForestGenerator","ForestEdgeGenerator","ForestRadialGenerator","ScrubGenerator","ScrubRadialGenerator"}.Contains(g.GetType().Name)).OrderBy(g=>g.GetType().Name,StringComparer.Ordinal).ToArray();
 Check(generators.Length==5,"generator catalog");
 string Node(int id,float x,float y) {var c=area.TerrainPointToLatLng(new TerrainPoint(x,y));return FormattableString.Invariant($"<node id=\"{id}\" lat=\"{c.Y:R}\" lon=\"{c.X:R}\"/>");}
 string Way(int id,int[] nodes,string tag,string val)=>$"<way id=\"{id}\">"+string.Concat(nodes.Select(n=>$"<nd ref=\"{n}\"/>"))+$"<tag k=\"{tag}\" v=\"{val}\"/></way>";
 string Rect(int id,float x,float y,float x2,float y2,string tag,string val){int n=id*10;return Node(n,x,y)+Node(n+1,x2,y)+Node(n+2,x2,y2)+Node(n+3,x,y2)+Way(id,new[]{n,n+1,n+2,n+3,n},tag,val);}
 // Deliberately unequal forest areas, one crosses logical sector x=240. Finite synthetic fixture only.
 var xml="<osm version=\"0.6\">"+Rect(100,140,80,300,230,"landuse","forest")+Rect(101,350,310,430,430,"landuse","forest")+Rect(102,60,310,165,420,"natural","scrub")+Rect(103,85,85,115,115,"natural","water")+Node(1,60,150)+Node(2,340,150)+Way(104,new[]{1,2},"highway","residential")+Node(3,180,200)+Node(4,260,200)+Way(105,new[]{3,4},"man_made","cutline")+"</osm>";
 var xmlHash=Hash(Encoding.UTF8.GetBytes(xml));
 var reviewed=new[]{typeof(ConditionEvaluator),typeof(ForestData),typeof(ForestEdgeData),typeof(ForestRadialData),typeof(ScrubData),typeof(ScrubRadialData),typeof(CategoryAreaData),typeof(CitiesData),typeof(OceanData),typeof(RoadsData),typeof(BuildingsData),typeof(RailwaysData),typeof(CutlinesData),typeof(LakesData)};
 async Task Reject(Func<Task> action,string type){try{await action();}catch(Exception ex) when(ex.GetBaseException() is InvalidOperationException && ex.GetBaseException().Message.Contains("Unreviewed builder")&&ex.GetBaseException().Message.Contains(type)){return;}throw new Exception("expected guarded refusal: "+type);}
 async Task<Dictionary<string,(string[] records,float[] z)>> Run(string state,int delta,bool probeSplit=false){
  Check(state is "abandoned" or "operational" or "unknown","state");
  var rows=Enumerable.Range(0,16).Select(y=>string.Join(" ",Enumerable.Range(0,16).Select(x=>100+x+2*(15-y)+delta)));
  var asc=Encoding.ASCII.GetBytes("ncols 16\nnrows 16\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n"+string.Join("\n",rows)+"\n");
  var prj=Encoding.ASCII.GetBytes("synthetic fixture only");
  var input=NodeInput.Parse(asc,prj,new NodeContract(16,30,1000,2000,"EPSG:32636","EGM2008","m",Hash(asc),Hash(prj),"synthetic fixture only"));var grid=input.CopyGrid();
  var osm=OsmDataSource.CreateFromInlineXml(xml);
  var ctx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,osm,map,new MemoryHugeImageStorage());
  try{
   ctx.SetData(new ElevationData(grid));
   var roads=await ctx.GetDataAsync<RoadsData>();var lakes=await ctx.GetDataAsync<LakesData>();var cuts=await ctx.GetDataAsync<CutlinesData>();var rails=await ctx.GetDataAsync<RailwaysData>();var buildings=await ctx.GetDataAsync<BuildingsData>();var ocean=await ctx.GetDataAsync<OceanData>();var categories=await ctx.GetDataAsync<CategoryAreaData>();
   Check(roads.Roads.Count==1&&lakes.Polygons.Count==1&&cuts.Polygons.Count==1&&rails.Railways.Count==0&&buildings.Buildings.Count==0&&ocean.Polygons.Count==0&&categories.Areas.Count==0,"bounded geometry support");
   // Explicit fixture inventory: no meadows, rocks, farmland, orchards, vineyards or relations. No claim of general closure.
   List<TerrainPolygon> Read(params long[] ids)=>osm.Ways.Where(w=>w.Id.HasValue&&ids.Contains(w.Id.Value)).SelectMany(w=>osm.Interpret(w)).SelectMany(g=>TerrainPolygon.FromGeometry(g,area.LatLngToTerrainPoint)).SelectMany(p=>p.ClippedBy(area.TerrainBounds)).ToList();
   var forest=Read(100,101);var scrub=Read(102);Check(forest.Count==2&&scrub.Count==1,"source count");
   var protect=lakes.Polygons.Concat(cuts.Polygons).Concat(rails.Railways.SelectMany(r=>r.ClearPolygons)).Concat(buildings.Buildings.Select(b=>b.Box.Polygon)).Concat(ocean.Polygons).Concat(categories.Areas.SelectMany(a=>a.PolyList)).ToList();
   if(state!="abandoned")protect.AddRange(roads.Roads.SelectMany(r=>r.ClearPolygons));
   List<TerrainPolygon> Minus(IEnumerable<TerrainPolygon> a,IEnumerable<TerrainPolygon> b)=>a.SelectMany(p=>p.SubstractAll(b)).ToList();
   var f=Minus(forest,protect);var s=Minus(scrub,protect.Concat(f));Check(f.Count>=2&&s.Count>0,"selected polygons");
   ctx.SetData(new ForestData(f));ctx.SetData(new ScrubData(s));
   // Actual native edge builder is safe with reviewed ForestData already set.
   var e=(await ctx.GetDataAsync<ForestEdgeData>()).Polygons;
   List<TerrainPolygon> Ring(List<TerrainPolygon> source,float width,IEnumerable<TerrainPolygon> priority)=>TerrainPolygon.MergeAll(Minus(source.SelectMany(p=>p.OuterCrown(width)).SelectMany(p=>p.ClippedBy(area.TerrainBounds)),priority));
   var fr=Ring(f,ForestRadialData.Width,protect.Concat(f).Concat(s));
   var sr=Ring(s,ScrubRadialData.Width,protect.Concat(f).Concat(s).Concat(fr));
   ctx.SetData(new ForestRadialData(fr));ctx.SetData(new ScrubRadialData(sr));
   var domains=new Dictionary<string,List<TerrainPolygon>>{{"ForestGenerator",f},{"ForestEdgeGenerator",e},{"ForestRadialGenerator",fr},{"ScrubGenerator",s},{"ScrubRadialGenerator",sr}};
   await Reject(async()=>{await ctx.GetDataAsync<RawElevationData>();},"RawElevationData");await Reject(async()=>{await ctx.GetDataAsync<ElevationWithLakesData>();},"ElevationWithLakesData");await Reject(async()=>{await ctx.GetDataAsync<ElevationOutOfBoundsData>();},"ElevationOutOfBoundsData");
   var result=new Dictionary<string,(string[] records,float[] z)>();
   foreach(var generator in generators){
    string name=generator.GetType().Name;var domain=domains[name];Check(domain.Count>0,"empty domain "+name);
    var objects=(await generator.Generate(map,ctx,new NoProgress())).ToArray();Check(objects.Length>0&&objects.Length<100000,"native count "+name);
    foreach(var o in objects)Check(o.IsValid&&o.ElevationMode==ElevationMode.Relative&&requested.Contains(o.Model.Path)&&ReferenceEquals(o.Model,resolver.ResolveByPath(o.Model.Path)),"native record model/mode");
    var road=objects.Count(o=>roads.Roads.Any(r=>r.Polygons.Any(p=>p.ContainsIncludingBorder(o.Point))));
    var outside=objects.Count(o=>!domain.Any(p=>p.ContainsIncludingBorder(o.Point)));
    var blocked=objects.Count(o=>protect.Any(p=>p.ContainsIncludingBorder(o.Point)));
    var review=objects.Where(o=>!domain.Any(p=>p.ContainsIncludingBorder(o.Point))||protect.Any(p=>p.ContainsIncludingBorder(o.Point))||o.Point.X<0||o.Point.X>=480||o.Point.Y<0||o.Point.Y>=480).ToArray();
    var accepted=objects.Except(review).ToArray(); // object instances, no silent movement
    var left=accepted.Where(o=>o.Point.X<240).ToArray();var right=accepted.Where(o=>o.Point.X>=240).ToArray();
    string[] Records(IEnumerable<TerrainBuilderObject> a)=>a.Select(o=>o.ToTerrainBuilderCSV()).OrderBy(x=>x,StringComparer.Ordinal).ToArray();
    Check(Records(left.Concat(right)).SequenceEqual(Records(accepted))&&left.Length+right.Length+review.Length==objects.Length,"half-open ownership");
    Check(!accepted.Any(o=>protect.Any(p=>p.ContainsIncludingBorder(o.Point))),"protected point escaped review");
    var sorted=objects.OrderBy(o=>o.ToTerrainBuilderCSV(),StringComparer.Ordinal).ToArray();var records=Records(objects);var z=sorted.Select(o=>o.ToWrpTransform(grid).M42).ToArray();
    Check(z.All(float.IsFinite)&&NodeInput.GridHash(grid)==input.Fingerprint,"grid or z");
    Console.WriteLine(FormattableString.Invariant($"{state} delta={delta} {name} polygons={domain.Count} records={objects.Length} road={road} outside={outside} protected={blocked} review={review.Length} left={left.Length} right={right.Length} duplicate_csv={records.Length-records.Distinct().Count()} sha={Hash(Encoding.UTF8.GetBytes(string.Join("\n",records)))}"));
    result.Add(name,(records,z));
   }
   // Contrast generating on globally complete polygons then assigning ownership with clipping first.
   if(probeSplit){
    var gen=generators.Single(g=>g.GetType().Name=="ForestGenerator");
    TerrainPolygon box(float a,float b)=>ReadBox(a,b);
    TerrainPolygon ReadBox(float a,float b)=>new TerrainPolygon(new List<TerrainPoint>{new(a,0),new(b,0),new(b,480),new(a,480),new(a,0)});
    var split=f.SelectMany(p=>p.ClippedBy(box(0,240)).Concat(p.ClippedBy(box(240,480)))).ToList();
    // New context to avoid cache mutation assumptions; only generator inputs preseeded, native evaluator dependencies remain guarded.
    var splitCtx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
    try{splitCtx.SetData(new ElevationData(grid));splitCtx.SetData(new ForestData(split));var splitRecords=(await gen.Generate(map,splitCtx,new NoProgress())).Select(o=>o.ToTerrainBuilderCSV()).OrderBy(x=>x,StringComparer.Ordinal).ToArray();var full=result["ForestGenerator"].records;Console.WriteLine($"CLIP_FIRST polygons={split.Count} count={splitRecords.Length} full_count={full.Length} identical={splitRecords.SequenceEqual(full)} common={splitRecords.Intersect(full).Count()}");}finally{splitCtx.DisposeHugeImages();}
   }
   Check(NodeInput.GridHash(grid)==input.Fingerprint,"final grid mutation");return result;
  }finally{ctx.DisposeHugeImages();}
 }
 // Native stock builder refusals verified separately, with source inputs preseeded where appropriate.
 var stock=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
 try{await Reject(async()=>{await stock.GetDataAsync<ScrubData>();},"ElevationWithLakesData");stock.SetData(new ForestData(new List<TerrainPolygon>()));stock.SetData(new ScrubData(new List<TerrainPolygon>()));await Reject(async()=>{await stock.GetDataAsync<ForestRadialData>();},"ElevationWithLakesData");await Reject(async()=>{await stock.GetDataAsync<ScrubRadialData>();},"ElevationWithLakesData");}finally{stock.DisposeHugeImages();}
 Console.WriteLine("STOCK_SCRUB_AND_RADIAL_REFUSED PASS");
 var a=await Run("abandoned",0,true);var b=await Run("abandoned",0);var c=await Run("abandoned",100);var d=await Run("operational",0);var u=await Run("unknown",0);
 foreach(var k in a.Keys){Check(a[k].records.SequenceEqual(b[k].records)&&a[k].z.SequenceEqual(b[k].z),"repeat mismatch "+k);Check(a[k].records.SequenceEqual(c[k].records)&&a[k].z.Zip(c[k].z,(x,y)=>Math.Abs(y-x-100)<0.001f).All(x=>x),"height shift "+k);Check(d[k].records.SequenceEqual(u[k].records),"unknown policy "+k);}
 Check(Hash(Encoding.UTF8.GetBytes(xml))==xmlHash&&Hash(File.ReadAllBytes(args[0]))==Hash(config)&&Hash(File.ReadAllBytes(args[1]))==Hash(cache),"source mutation");
 Console.WriteLine("PASS five native layers; synthetic final point review and global ownership only");return 0;
} catch(Exception e){Console.Error.WriteLine("REJECTED: "+e);return 2;}
sealed class ReviewModels:IModelInfoLibrary {
 readonly Dictionary<string,ModelInfo> byPath,byName;
 public HashSet<string> Seen {get;}=new(StringComparer.OrdinalIgnoreCase);
 public ReviewModels(IEnumerable<ModelInfo> models){byPath=models.ToDictionary(m=>m.Path,StringComparer.OrdinalIgnoreCase);byName=byPath.Values.ToDictionary(m=>m.Name,StringComparer.OrdinalIgnoreCase);}
 public bool TryResolveByPath(string path,[MaybeNullWhen(false)] out ModelInfo model){if(byPath.TryGetValue(path,out model)){Seen.Add(path);return true;}return false;}
 public bool TryResolveByName(string name,[MaybeNullWhen(false)] out ModelInfo model)=>byName.TryGetValue(name,out model);
 public ModelInfo ResolveByPath(string path)=>TryResolveByPath(path,out var m)?m:throw new InvalidOperationException("unreviewed path");
 public ModelInfo ResolveByName(string name)=>TryResolveByName(name,out var m)?m:throw new InvalidOperationException("unreviewed name");
 public bool TryRegister(string name,string path)=>false;
 public bool? IsSlopeLandContact(string path)=>null;
 public string? TryGetNoLandContact(string path)=>null;
}
