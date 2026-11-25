using GameRealisticMap.ManMade.Fences;
using GameRealisticMap.Arma3.Assets.Rows;
using GameRealisticMap.ManMade.Roads.Libraries;
using GameRealisticMap.Arma3.GameEngine;
using GameRealisticMap.Arma3.GameEngine.Roads;
using GameRealisticMap.Arma3.IO;
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

 var lib=(IArma3RegionAssets)assets;
 Check(assets.Sidewalks.Count==0 && assets.Roads.All(r=>r.HasSideWalks==false&&r.ProceduralStreetLamps==StreetLampsCondition.None),"v03 procedural flags");
 Check(lib.GetObjects(ObjectTypeId.StreetLamp).Count==2,"explicit lamp configs");
 var generators=new Arma3LayerGeneratorCatalog(assets).Generators.Where(g=>new[]{"FenceGenerator","OrientedObjectsGenerator","TreeRowsGenerator","SidewalksGenerator"}.Contains(g.GetType().Name)).OrderBy(g=>g.GetType().Name).ToArray();
 Check(generators.Length==4,"native generator count");
 string Tag(string k,string v)=>$"<tag k=\"{k}\" v=\"{v}\"/>";
 string Node(int id,float x,float y,string tags="") {var c=area.TerrainPointToLatLng(new TerrainPoint(x,y));return FormattableString.Invariant($"<node id=\"{id}\" lat=\"{c.Y:R}\" lon=\"{c.X:R}\">{tags}</node>");}
 string Way(int id,int[] nodes,string tags)=>$"<way id=\"{id}\">"+string.Concat(nodes.Select(n=>$"<nd ref=\"{n}\"/>"))+tags+"</way>";
 var xml="<osm version=\"0.6\">"+Node(1,60,120)+Node(2,420,120)+Way(101,new[]{1,2},Tag("highway","residential"))
 +Node(3,60,240)+Node(4,140,240)+Way(102,new[]{3,4},Tag("barrier","fence"))
 +Node(5,180,240)+Node(6,220,240)+Node(7,220,280)+Way(103,new[]{5,6,7},Tag("barrier","wall"))
 +Node(8,260,240)+Node(9,340,240)+Way(104,new[]{8,9},Tag("barrier","hedge"))
 +Node(10,360,90)+Node(11,360,150)+Way(105,new[]{10,11},Tag("barrier","fence"))
 +Node(12,60,330)+Node(13,260,330)+Way(106,new[]{12,13},Tag("natural","tree_row"))
 +Node(14,320,300)+Node(15,400,300)+Way(107,new[]{14,15},Tag("barrier","retaining_wall"))
 +Node(16,100,240,Tag("barrier","gate"))
 +Node(17,100,140,Tag("amenity","bench")+Tag("direction","90"))
 +Node(18,140,140,Tag("amenity","waste_basket"))
 +Node(19,180,140,Tag("highway","street_lamp"))
 +Node(20,260,180,Tag("man_made","water_well"))
 +Node(21,300,180,Tag("man_made","flagpole"))
 +Node(22,340,180,Tag("amenity","post_box"))
 +Node(23,380,180,Tag("power","pole"))
 +Node(24,40,60)+Node(25,440,60)+Node(26,440,200)+Node(27,40,200)+Way(108,new[]{24,25,26,27,24},Tag("landuse","residential"))
 +"</osm>";
 var xmlHash=Hash(Encoding.UTF8.GetBytes(xml));
 var reviewed=new[]{typeof(RoadsData),typeof(RailwaysData),typeof(CategoryAreaData),typeof(CitiesData),typeof(OceanData),typeof(ConditionEvaluator),typeof(FencesData),typeof(OrientedObjectData),typeof(ProceduralStreetLampsData),typeof(TreeRowsData)};
 async Task Reject(Func<Task> action,string expected){try{await action();}catch(Exception e) when(e.GetBaseException() is InvalidOperationException && e.GetBaseException().Message.Contains(expected)){return;}throw new Exception("missing refusal "+expected);}
 async Task<(string[] records,float[] z)> Run(int delta){
  var rows=Enumerable.Range(0,16).Select(y=>string.Join(" ",Enumerable.Range(0,16).Select(x=>100+x+2*(15-y)+delta)));
  var asc=Encoding.ASCII.GetBytes("ncols 16\nnrows 16\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n"+string.Join("\n",rows)+"\n");
  var prj=Encoding.ASCII.GetBytes("synthetic fixture only");
  var input=NodeInput.Parse(asc,prj,new NodeContract(16,30,1000,2000,"EPSG:32636","EGM2008","m",Hash(asc),Hash(prj),"synthetic fixture only"));
  var grid=input.CopyGrid();var ctx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
  try {
   ctx.SetData(new ElevationData(grid));
   await Reject(async()=>{await ctx.GetDataAsync<RawElevationData>();},"RawElevationData");await Reject(async()=>{await ctx.GetDataAsync<ElevationWithLakesData>();},"ElevationWithLakesData");await Reject(async()=>{await ctx.GetDataAsync<ElevationOutOfBoundsData>();},"ElevationOutOfBoundsData");
   var roads=(await ctx.GetDataAsync<RoadsData>()).Roads;var fences=(await ctx.GetDataAsync<FencesData>()).Fences;var points=(await ctx.GetDataAsync<OrientedObjectData>()).Objects;var lamps=(await ctx.GetDataAsync<ProceduralStreetLampsData>()).Objects;var treeRows=(await ctx.GetDataAsync<TreeRowsData>()).Rows;
   Check(roads.Count==1&&fences.Count==4&&treeRows.Count==1&&points.Count==6&&lamps.Count==0,"native fixture counts");
   Check(points.Single(o=>o.TypeId==ObjectTypeId.Bench).Angle==-90,"explicit direction");
   Check(points.Count(o=>o.TypeId==ObjectTypeId.PostBox)==1&&lib.GetObjects(ObjectTypeId.PostBox).Count==0,"unconfigured post box");
   Console.WriteLine($"delta={delta} roads={roads.Count} fences={fences.Count} tree_rows={treeRows.Count} oriented={points.Count} procedural_lamps={lamps.Count} retaining_wall_omitted=true gate_omitted=true power_pole_omitted=true postbox_unconfigured=true");
   var output=new List<TerrainBuilderObject>();
   foreach(var g in generators){var items=(await g.Generate(map,ctx,new NoProgress())).ToArray();var name=g.GetType().Name;
    Check(name=="SidewalksGenerator"?items.Length==0:items.Length>0,"layer count "+name);
    Check(items.All(o=>o.IsValid&&o.ElevationMode==ElevationMode.Relative&&requested.Contains(o.Model.Path)&&ReferenceEquals(o.Model,resolver.ResolveByPath(o.Model.Path))&&float.IsFinite(o.Elevation)&&float.IsFinite(o.Pitch)&&float.IsFinite(o.Roll)&&o.Point.X>=0&&o.Point.X<480&&o.Point.Y>=0&&o.Point.Y<480),"record validation "+name);
    var onRoad=items.Count(o=>roads.Any(r=>r.Polygons.Any(p=>p.Contains(o.Point))));
    Console.WriteLine($"{name} records={items.Length} models={items.Select(o=>o.Model.Path).Distinct().Count()} on_road_points={onRoad}");
    if(name=="FenceGenerator") {Check(onRoad>0,"expected crossing fence review");var nearGate=items.Min(o=>Vector2.Distance(o.Point.Vector,new Vector2(100,240)));Console.WriteLine(FormattableString.Invariant($"gate_nearest_model_point_m={nearGate:F3} gate_opening_not_proven"));}
    if(name=="OrientedObjectsGenerator") {Check(items.Length==5,"explicit objects only");Check(items.Count(o=>o.Model.Path.Contains("lampstreet",StringComparison.OrdinalIgnoreCase))==1,"explicit lamp retained");}
    output.AddRange(items);
   }
   var sorted=output.OrderBy(o=>o.ToTerrainBuilderCSV(),StringComparer.Ordinal).ToArray();var records=sorted.Select(o=>o.ToTerrainBuilderCSV()).ToArray();var z=sorted.Select(o=>o.ToWrpTransform(grid).M42).ToArray();
   Check(records.Distinct().Count()==records.Length&&z.All(float.IsFinite),"record duplicates or nonfinite Z");
   Check(NodeInput.GridHash(grid)==input.Fingerprint,"grid mutation");
   Console.WriteLine($"total={records.Length} records_sha={Hash(Encoding.UTF8.GetBytes(string.Join("\n",records)))} grid_sha={input.Fingerprint}");return(records,z);
  }finally{ctx.DisposeHugeImages();}
 }
 var missing=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed.Where(t=>t!=typeof(RoadsData))),new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
 try{await Reject(async()=>{await missing.GetDataAsync<OrientedObjectData>();},"RoadsData");}finally{missing.DisposeHugeImages();}
 var a=await Run(0);var b=await Run(0);var c=await Run(100);
 Check(a.records.SequenceEqual(b.records)&&a.z.SequenceEqual(b.z),"repeat mismatch");Check(a.records.SequenceEqual(c.records)&&a.z.Zip(c.z,(x,y)=>Math.Abs(y-x-100)<0.001f).All(x=>x),"height response");
 Check(Hash(File.ReadAllBytes(args[0]))==Hash(config)&&Hash(File.ReadAllBytes(args[1]))==Hash(cache)&&Hash(Encoding.UTF8.GetBytes(xml))==xmlHash,"input mutation");
 Console.WriteLine("PASS bounded infrastructure; no real export, physical geometry or runtime approval");return 0;
}catch(Exception e){Console.Error.WriteLine("REJECTED: "+e);return 2;}
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
