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
 var generator=new Arma3LayerGeneratorCatalog(assets).Generators.Single(g=>g.GetType().Name=="ForestGenerator");
 var clusters=assets.GetClusterCollections(ClusterCollectionId.Forest);
 var additional=assets.GetBasicCollections(BasicCollectionId.ForestAdditional);
 Console.WriteLine($"CONFIG forest_cluster_collections={clusters.Count} additional_collections={additional.Count}");
 Check(clusters.Count>0,"forest config missing");
 string Node(int id,float x,float y) {var c=area.TerrainPointToLatLng(new TerrainPoint(x,y));return FormattableString.Invariant($"<node id=\"{id}\" lat=\"{c.Y:R}\" lon=\"{c.X:R}\"/>");}
 string Way(int id,int[] nodes,string tag,string val)=>$"<way id=\"{id}\">"+string.Concat(nodes.Select(n=>$"<nd ref=\"{n}\"/>"))+$"<tag k=\"{tag}\" v=\"{val}\"/></way>";
 // All fixtures are bounded synthetic geometry; one forest polygon, interior road and water/cutline.
 var xml="<osm version=\"0.6\">"+Node(1,60,60)+Node(2,420,60)+Node(3,420,420)+Node(4,60,420)+Way(100,new[]{1,2,3,4,1},"landuse","forest")+Node(5,110,240)+Node(6,370,240)+Way(101,new[]{5,6},"highway","residential")+Node(7,100,100)+Node(8,145,100)+Node(9,145,145)+Node(10,100,145)+Way(102,new[]{7,8,9,10,7},"natural","water")+Node(11,150,350)+Node(12,330,350)+Way(103,new[]{11,12},"man_made","cutline")+"</osm>";
 var xmlHash=Hash(Encoding.UTF8.GetBytes(xml));
 var reviewed=new[]{typeof(ConditionEvaluator),typeof(ForestData),typeof(CategoryAreaData),typeof(CitiesData),typeof(OceanData),typeof(RoadsData),typeof(BuildingsData),typeof(RailwaysData),typeof(CutlinesData),typeof(LakesData)};
 async Task Reject(Func<Task> action,string type){try{await action();}catch(Exception ex) when(ex.GetBaseException() is InvalidOperationException && ex.GetBaseException().Message.Contains("Unreviewed builder")&&ex.GetBaseException().Message.Contains(type)){return;}throw new Exception("expected guarded refusal: "+type);}
 // Direct native forest builder still asks for mutating elevation stage; demonstrate rejection, not fake cache.
 var stock=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
 try{await Reject(async()=>{await stock.GetDataAsync<ForestData>();},"ElevationWithLakesData");}finally{stock.DisposeHugeImages();}
 Console.WriteLine("STOCK_FOREST_BUILDER_REFUSED PASS ElevationWithLakesData");
 async Task<(string[] records,float[] z,int roadCount)> Run(string state,int delta){
  Check(state is "abandoned" or "operational" or "unknown","unreviewed state");
  var rows=Enumerable.Range(0,16).Select(y=>string.Join(" ",Enumerable.Range(0,16).Select(x=>100+x+2*(15-y)+delta)));
  var asc=Encoding.ASCII.GetBytes("ncols 16\nnrows 16\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n"+string.Join("\n",rows)+"\n");
  var prj=Encoding.ASCII.GetBytes("synthetic fixture only");
  var input=NodeInput.Parse(asc,prj,new NodeContract(16,30,1000,2000,"EPSG:32636","EGM2008","m",Hash(asc),Hash(prj),"synthetic fixture only"));var grid=input.CopyGrid();
  var osm=OsmDataSource.CreateFromInlineXml(xml);
  var ctx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,osm,map,new MemoryHugeImageStorage());
  try{
   ctx.SetData(new ElevationData(grid));
   var roads=await ctx.GetDataAsync<RoadsData>();var lakes=await ctx.GetDataAsync<LakesData>();var cuts=await ctx.GetDataAsync<CutlinesData>();var rails=await ctx.GetDataAsync<RailwaysData>();var buildings=await ctx.GetDataAsync<BuildingsData>();
   Check(roads.Roads.Count==1&&lakes.Polygons.Count==1&&cuts.Polygons.Count==1&&rails.Railways.Count==0&&buildings.Buildings.Count==0,"native geometry support");
   // Explicit bounded policy seam, use native OSM interpretation and GRM polygon boolean operations. No duplicate forest fill algorithm.
   var source=osm.Ways.Single(w=>w.Id==100);
   var forest=osm.Interpret(source).SelectMany(g=>TerrainPolygon.FromGeometry(g,area.LatLngToTerrainPoint)).SelectMany(p=>p.ClippedBy(area.TerrainBounds)).ToList();
   Check(forest.Count==1,"synthetic forest source polygon");
   var protectedPolygons=lakes.Polygons.Concat(cuts.Polygons).Concat(rails.Railways.SelectMany(r=>r.ClearPolygons)).Concat(buildings.Buildings.Select(b=>b.Box.Polygon)).ToList();
   if(state!="abandoned")protectedPolygons.AddRange(roads.Roads.SelectMany(r=>r.ClearPolygons));
   var selected=forest.SelectMany(p=>p.SubstractAll(protectedPolygons)).ToList();
   Check(selected.Count==1&&selected[0].Area>0,"bounded one-polygon fixture");
   var sourceArea=forest.Sum(p=>p.Area); var selectedArea=selected.Sum(p=>p.Area);
   Check(selectedArea<sourceArea,"geometry exclusions");
   ctx.SetData(new ForestData(selected));
   await Reject(async()=>{await ctx.GetDataAsync<RawElevationData>();},"RawElevationData");await Reject(async()=>{await ctx.GetDataAsync<ElevationWithLakesData>();},"ElevationWithLakesData");await Reject(async()=>{await ctx.GetDataAsync<ElevationOutOfBoundsData>();},"ElevationOutOfBoundsData");
   var objects=(await generator.Generate(map,ctx,new NoProgress())).ToArray();
   Check(objects.Length>0&&objects.Length<100000,"native forest count bounds");
   foreach(var o in objects)Check(o.IsValid&&o.ElevationMode==ElevationMode.Relative&&requested.Contains(o.Model.Path)&&ReferenceEquals(o.Model,resolver.ResolveByPath(o.Model.Path)),"native record model/mode");
   var roadCount=objects.Count(o=>roads.Roads.Any(r=>r.Polygons.Any(p=>p.ContainsIncludingBorder(o.Point))));
   var lakeCount=objects.Count(o=>lakes.Polygons.Any(p=>p.ContainsIncludingBorder(o.Point)));
   var cutCount=objects.Count(o=>cuts.Polygons.Any(p=>p.ContainsIncludingBorder(o.Point)));
   var outsideCount=objects.Count(o=>!forest.Any(p=>p.ContainsIncludingBorder(o.Point)));
   // Final anchor validation is a review measurement, not physical geometry or an exporter.
   var review=objects.Count(o=>protectedPolygons.Any(p=>p.ContainsIncludingBorder(o.Point))||!forest.Any(p=>p.ContainsIncludingBorder(o.Point)));
   Check(lakeCount==0&&cutCount==0,"protected water/cutline anchor overlap");
   Check(state=="abandoned" ? roadCount>0 : roadCount==0,"road policy failed at final model point");
   Check(review>=outsideCount&&outsideCount>0,"expected final-offset review fixture");
   var sorted=objects.OrderBy(o=>o.ToTerrainBuilderCSV(),StringComparer.Ordinal).ToArray();var records=sorted.Select(o=>o.ToTerrainBuilderCSV()).ToArray();var z=sorted.Select(o=>o.ToWrpTransform(grid).M42).ToArray();
   Check(z.All(float.IsFinite)&&NodeInput.GridHash(grid)==input.Fingerprint,"grid or z");
   Console.WriteLine(FormattableString.Invariant($"FOREST state={state} delta={delta} source_m2={sourceArea:F2} selected_m2={selectedArea:F2} records={records.Length} models={objects.Select(o=>o.Model.Path).Distinct(StringComparer.OrdinalIgnoreCase).Count()} on_road={roadCount} in_lake={lakeCount} in_cutline={cutCount} outside={outsideCount} final_review={review} grid={input.Fingerprint} records_sha={Hash(Encoding.UTF8.GetBytes(string.Join("\n",records)))}"));
   return(records,z,roadCount);
  }finally{ctx.DisposeHugeImages();}
 }
 var a=await Run("abandoned",0); var b=await Run("abandoned",0); var c=await Run("abandoned",100); var d=await Run("operational",0);var unknownRun=await Run("unknown",0);
 Check(a.records.SequenceEqual(b.records)&&a.z.SequenceEqual(b.z),"native repeat");
 Check(a.records.SequenceEqual(c.records)&&a.z.Zip(c.z,(x,y)=>Math.Abs(y-x-100)<0.001f).All(x=>x),"relative elevation shift mismatch");
 Check(a.roadCount>0,"fixture no abandoned road placement");
 Check(d.records.SequenceEqual(unknownRun.records),"unknown should not authorize road overlap");
 Check(Hash(Encoding.UTF8.GetBytes(xml))==xmlHash&&Hash(File.ReadAllBytes(args[0]))==Hash(config)&&Hash(File.ReadAllBytes(args[1]))==Hash(cache),"source mutation");
 Console.WriteLine("PASS bounded synthetic native ForestGenerator; no production output; final overlap review counts are not approval");return 0;
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
