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
 var candidates=assets.GetObjects(ObjectTypeId.Tree);
 Check(candidates.Count==5,"expected five tree definitions");
 var treePaths=candidates.SelectMany(c=>c.Composition.Objects).Select(o=>o.Model.Path).ToHashSet(StringComparer.OrdinalIgnoreCase);
 Check(treePaths.Count==5,"tree model paths");
 var map=new Arma3MapConfig(new Arma3MapConfigJson {Center="9 N, 33 E",GridSize=16,GridCellSize=30,WorldName="synthetic_only",TargetModDirectory="unused",TileSize=512});
 var area=map.TerrainArea;
 var generator=new Arma3LayerGeneratorCatalog(assets).Generators.Single(g=>g.GetType().Name=="TreesGenerator");
 string Node(int id,float x,float y,string tags="") {var c=area.TerrainPointToLatLng(new TerrainPoint(x,y));return FormattableString.Invariant($"<node id=\"{id}\" lat=\"{c.Y:R}\" lon=\"{c.X:R}\">{tags}</node>");}
 string Way(int id,int[] nodes,string tags)=>$"<way id=\"{id}\">"+string.Concat(nodes.Select(n=>$"<nd ref=\"{n}\"/>"))+tags+"</way>";
 string Tag(string k,string v)=>$"<tag k=\"{k}\" v=\"{v}\"/>";
 var xml="<osm version=\"0.6\">";
 // Road length 300m; building and landuse polygons; a city, and a tree just outside road polygon.
 xml+=Node(1,60,120)+Node(2,360,120)+Way(101,new[]{1,2},Tag("highway","residential"));
 xml+=Node(3,260,260)+Node(4,280,260)+Node(5,280,280)+Node(6,260,280)+Way(102,new[]{3,4,5,6,3},Tag("building","yes"));
 xml+=Node(7,220,220)+Node(8,350,220)+Node(9,350,350)+Node(10,220,350)+Way(103,new[]{7,8,9,10,7},Tag("landuse","residential"));
 xml+=Node(11,320,320,Tag("place","village")+Tag("name","Synthetic"));
 // Actual GRM road width is 7m for residential; point at 124.5m is 1m outside road.
 xml+=Node(20,180,124.5f,Tag("natural","tree"));
 var testPoints=new List<TerrainPoint>();
 for(int y=0;y<5;y++)for(int x=0;x<5;x++){var pt=new TerrainPoint(60+30*x,210+30*y);testPoints.Add(pt);xml+=Node(21+x+5*y,pt.X,pt.Y,Tag("natural","tree"));}
 xml+="</osm>";
 var reviewed=new[]{typeof(ConditionEvaluator),typeof(TreesData),typeof(CategoryAreaData),typeof(CitiesData),typeof(OceanData),typeof(RoadsData),typeof(BuildingsData)};
 async Task Reject(Func<Task> action){try{await action();}catch(Exception ex) when(ex.GetBaseException() is InvalidOperationException && ex.GetBaseException().Message.Contains("Unreviewed builder")){return;}throw new Exception("expected guarded refusal");}
 async Task<(string[] records,float[] z)> Run(int delta){
  var rows=Enumerable.Range(0,16).Select(y=>string.Join(" ",Enumerable.Range(0,16).Select(x=>100+x+2*(15-y)+delta)));
  var asc=Encoding.ASCII.GetBytes("ncols 16\nnrows 16\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n"+string.Join("\n",rows)+"\n");
  var prj=Encoding.ASCII.GetBytes("synthetic fixture only");
  var input=NodeInput.Parse(asc,prj,new NodeContract(16,30,1000,2000,"EPSG:32636","EGM2008","m",Hash(asc),Hash(prj),"synthetic fixture only"));
  var grid=input.CopyGrid();
  var guard=new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed);
  var ctx=new BuildContext(guard,new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
  try {
   ctx.SetData(new ElevationData(grid)); // only injected type; all other data genuinely built from OSM
   await Reject(async()=>{await ctx.GetDataAsync<RawElevationData>();});await Reject(async()=>{await ctx.GetDataAsync<ElevationWithLakesData>();});await Reject(async()=>{await ctx.GetDataAsync<ElevationOutOfBoundsData>();});
   var objects=(await generator.Generate(map,ctx,new NoProgress())).ToArray();
   var roads=await ctx.GetDataAsync<RoadsData>();var buildings=await ctx.GetDataAsync<BuildingsData>();var areas=await ctx.GetDataAsync<CategoryAreaData>();var cities=await ctx.GetDataAsync<CitiesData>();var ocean=await ctx.GetDataAsync<OceanData>();var trees=await ctx.GetDataAsync<TreesData>();
   Check(roads.Roads.Count==1&&buildings.Buildings.Count==1&&areas.Areas.Count==1&&cities.Cities.Count==1&&ocean.Polygons.Count==0,"native support counts");
   Check(trees.Points.Count==26&&objects.Length==26,"native tree/record counts");
   var near=trees.Points.MinBy(p=>Vector2.Distance(p.Vector,new Vector2(180,124.5f))) ?? throw new InvalidDataException("no trees");
   var distance=roads.Roads[0].Polygons.Min(p=>p.Distance(near));
   Check(distance>=1.99f&&distance<=2.01f,"road clearance near edge "+distance);
   foreach(var o in objects)Check(o.IsValid&&o.ElevationMode==ElevationMode.Relative&&treePaths.Contains(o.Model.Path)&&ReferenceEquals(o.Model,resolver.ResolveByPath(o.Model.Path)),"native record model/mode");
   var sorted=objects.OrderBy(o=>o.ToTerrainBuilderCSV(),StringComparer.Ordinal).ToArray();
   var records=sorted.Select(o=>o.ToTerrainBuilderCSV()).ToArray();var z=sorted.Select(o=>o.ToWrpTransform(grid).M42).ToArray();
   Check(z.All(float.IsFinite),"nonfinite z"); Check(NodeInput.GridHash(grid)==input.Fingerprint,"grid mutation");
   Console.WriteLine(FormattableString.Invariant($"delta={delta} roads={roads.Roads.Count} buildings={buildings.Buildings.Count} areas={areas.Areas.Count} cities={cities.Cities.Count} trees={trees.Points.Count} records={objects.Length} distinct_models={objects.Select(o=>o.Model.Path).Distinct().Count()} road_clearance_m={distance:F4} grid={input.Fingerprint} records_sha={Hash(Encoding.UTF8.GetBytes(string.Join("\n",records)))}"));
   return (records,z);
  } finally {ctx.DisposeHugeImages();}
 }
 // Verify that the allowlist cannot silently fill an absent dependency.
 var missingGuard=new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed.Where(t=>t!=typeof(RoadsData)));
 var missingCtx=new BuildContext(missingGuard,new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
 try {await Reject(async()=>{await missingCtx.GetDataAsync<TreesData>();});}
 finally {missingCtx.DisposeHugeImages();}
 Console.WriteLine("MISSING_ROADS_DEPENDENCY_REFUSED PASS");
 // Independent negative observation: a point inside a wide road is NOT guaranteed to escape it.
 var insideXml=xml.Replace("</osm>",Node(90,300,120,Tag("natural","tree"))+"</osm>");
 var insideCtx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,OsmDataSource.CreateFromInlineXml(insideXml),map,new MemoryHugeImageStorage());
 try {
  var insideTrees=await insideCtx.GetDataAsync<TreesData>();var insideRoads=await insideCtx.GetDataAsync<RoadsData>();
  Check(insideTrees.Points.Count==27,"inside fixture count");
  var inside=insideTrees.Points.MinBy(p=>Vector2.Distance(p.Vector,new Vector2(300,120))) ?? throw new InvalidDataException("no interior tree");
  var d=insideRoads.Roads.Single().Polygons.Min(p=>p.Distance(inside));
  Console.WriteLine(FormattableString.Invariant($"INTERIOR_ROAD_PROBE clearance_m={d:F4} production_clearance_gate={(d>=1.99f?"PASS":"FAIL")}"));
 } finally {insideCtx.DisposeHugeImages();}
 var a=await Run(0);var b=await Run(0);var c=await Run(100);
 Check(a.records.SequenceEqual(b.records)&&a.z.SequenceEqual(b.z),"repeat mismatch");
 Check(a.records.SequenceEqual(c.records)&&a.z.Zip(c.z,(x,y)=>Math.Abs(y-x-100)<0.001f).All(x=>x),"relative elevation shift mismatch");
 Check(Hash(File.ReadAllBytes(args[0]))==Hash(config)&&Hash(File.ReadAllBytes(args[1]))==Hash(cache),"source mutation");
 Console.WriteLine("PASS native v03 TreesGenerator, seven reviewed builder types, actual metadata, repeat, +100m relative Z, no height mutation; synthetic only");return 0;
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
