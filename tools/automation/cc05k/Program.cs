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

 var generators=new Arma3LayerGeneratorCatalog(assets).Generators.Where(g=>new[]{"RailwayGenerator","BridgeGenerator"}.Contains(g.GetType().Name)).OrderBy(g=>g.GetType().Name).ToArray();
 Check(generators.Length==2,"native catalog");
 string Tag(string k,string v)=>$"<tag k=\"{k}\" v=\"{v}\"/>";
 string Node(int id,float x,float y,string tags="") {var c=area.TerrainPointToLatLng(new TerrainPoint(x,y));return FormattableString.Invariant($"<node id=\"{id}\" lat=\"{c.Y:R}\" lon=\"{c.X:R}\">{tags}</node>");}
 string Way(int id,int[] nodes,string tags)=>$"<way id=\"{id}\">"+string.Concat(nodes.Select(n=>$"<nd ref=\"{n}\"/>"))+tags+"</way>";
 var xml="<osm version=\"0.6\">"+Node(1,60,120)+Node(2,240,120,Tag("railway","level_crossing"))+Node(3,420,120)
  +Way(101,new[]{1,2},Tag("highway","residential"))+Way(102,new[]{2,3},Tag("highway","residential"))
  +Node(4,240,60)+Node(5,240,210)+Way(103,new[]{4,2,5},Tag("railway","rail"))
  +Node(6,60,240)+Node(7,180,240)+Way(104,new[]{6,7},Tag("highway","track"))
  +Node(8,60,330)+Node(9,180,330)+Way(105,new[]{8,9},Tag("highway","primary")+Tag("bridge","yes"))
  +Node(10,300,330)+Node(11,330,330)+Way(106,new[]{10,11},Tag("highway","primary")+Tag("bridge","yes"))
  +Node(12,60,390)+Node(13,70,390)+Way(107,new[]{12,13},Tag("highway","service")+Tag("access","private"))
  +Node(14,300,390)+Node(15,420,390)+Way(108,new[]{14,15},Tag("railway","disused"))
  +"</osm>";
 var xmlHash=Hash(Encoding.UTF8.GetBytes(xml));
 var reviewed=new[]{typeof(RoadsData),typeof(RailwaysData)};
 async Task Reject(Func<Task> action,string expected){try{await action();}catch(Exception e) when(e.GetBaseException() is InvalidOperationException && e.GetBaseException().Message.Contains(expected)){return;}throw new Exception("missing refusal "+expected);}
 string RoadKey(Road r)=>r.RoadType+":"+r.SpecialSegment+":"+string.Join(";",r.Path.Points.Select(p=>FormattableString.Invariant($"{p.X:R},{p.Y:R}")));
 string RailKey(Railway r)=>r.SpecialSegment+":"+string.Join(";",r.Path.Points.Select(p=>FormattableString.Invariant($"{p.X:R},{p.Y:R}")));
 async Task<(string roads,string rails,string files,string[] objects,float[] z,float[] absolute,int[] modes)> Run(int delta){
  var rows=Enumerable.Range(0,16).Select(y=>string.Join(" ",Enumerable.Range(0,16).Select(x=>100+x+2*(15-y)+delta)));
  var asc=Encoding.ASCII.GetBytes("ncols 16\nnrows 16\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n"+string.Join("\n",rows)+"\n");
  var prj=Encoding.ASCII.GetBytes("synthetic fixture only");
  var input=NodeInput.Parse(asc,prj,new NodeContract(16,30,1000,2000,"EPSG:32636","EGM2008","m",Hash(asc),Hash(prj),"synthetic fixture only"));
  var grid=input.CopyGrid();var ctx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
  try{
   ctx.SetData(new ElevationData(grid));
   await Reject(async()=>{await ctx.GetDataAsync<RawElevationData>();},"RawElevationData");await Reject(async()=>{await ctx.GetDataAsync<ElevationWithLakesData>();},"ElevationWithLakesData");await Reject(async()=>{await ctx.GetDataAsync<ElevationOutOfBoundsData>();},"ElevationOutOfBoundsData");
   var roads=(await ctx.GetDataAsync<RoadsData>()).Roads;var rails=(await ctx.GetDataAsync<RailwaysData>()).Railways;
   Console.WriteLine("roads "+string.Join(" | ",roads.Select(RoadKey)));Console.WriteLine("rails "+string.Join(" | ",rails.Select(RailKey)));
   Check(roads.Count==3,"road count "+roads.Count);Check(roads.Count(r=>r.SpecialSegment==WaySpecialSegment.Bridge)==1,"bridge count");
   var merged=roads.Single(r=>r.RoadType==RoadTypeId.TwoLanesConcreteRoad);Check(merged.Path.Points.Count==3&&Math.Abs(merged.Path.Length-360)<0.1,"merged road");
   Check(rails.Count==4&&rails.Count(r=>r.SpecialSegment==WaySpecialSegment.Crossing)==1,"rail crossing split");
   var roadBefore=string.Join("\n",roads.Select(RoadKey).Order());var railBefore=string.Join("\n",rails.Select(RailKey).Order());
   // Exercise stock road compiler and stock reader; four output streams never touch disk.
   var fs=new ReviewFileSystem(map.PboPrefix+"\\data\\roads");
   new RoadsCompiler(new NoProgress(),fs,((IArma3RegionAssets)assets).RoadTypeLibrary).Write(map,roads);
   Check(fs.Files.Count==4,"four road streams");
   var round=new RoadsDeserializer(fs).Deserialize(fs.Prefix);
   Check(round.RoadTypeInfos.Count==9&&round.Roads.Count==2,"road roundtrip");
   foreach(var r in round.RoadTypeInfos){var src=((IArma3RegionAssets)assets).RoadTypeLibrary.GetInfo((RoadTypeId)(r.Id-1));Check(src.Texture==r.Texture&&src.TextureEnd==r.TextureEnd&&src.Material==r.Material&&src.TextureWidth==r.TextureWidth,"road profile mismatch");}
   foreach(var r in round.Roads){var original=roads.Single(o=>o.SpecialSegment!=WaySpecialSegment.Bridge&&(int)o.RoadType+1==r.RoadTypeInfos.Id);Check(r.Order==r.RoadTypeInfos.Id,"road ORDER");Check(Vector2.Distance(r.Path.FirstPoint.Vector,original.Path.FirstPoint.Vector)<0.02f&&Vector2.Distance(r.Path.LastPoint.Vector,original.Path.LastPoint.Vector)<0.02f,"road endpoint shift");Check(r.Path.Points.All(p=>p.X>=0&&p.X<480&&p.Y>=0&&p.Y<480),"road bounds");}
   // DBF header contains date; only compare decoded geometry and profiles across process runs, not raw DBF bytes.
   var fileFingerprint=Hash(Encoding.UTF8.GetBytes(string.Join("\n",round.Roads.Select(r=>r.RoadTypeInfos.Id+":"+r.Order+":"+string.Join(";",r.Path.Points.Select(p=>FormattableString.Invariant($"{p.X:R},{p.Y:R}")))).Order())+"\n"+Encoding.UTF8.GetString(fs.Files[fs.Prefix+"\\roadslib.cfg"])));
   var allObjects=new List<TerrainBuilderObject>();
   foreach(var generator in generators){var objs=(await generator.Generate(map,ctx,new NoProgress())).ToArray();Check(objs.Length>0,"empty "+generator.GetType().Name);var expect=generator.GetType().Name=="BridgeGenerator"?ElevationMode.Absolute:ElevationMode.Relative;
    Check(objs.All(o=>o.IsValid&&o.ElevationMode==expect&&requested.Contains(o.Model.Path)&&ReferenceEquals(o.Model,resolver.ResolveByPath(o.Model.Path))&&float.IsFinite(o.Elevation)&&float.IsFinite(o.Pitch)&&float.IsFinite(o.Roll)&&o.Point.X>=0&&o.Point.X<480&&o.Point.Y>=0&&o.Point.Y<480),"record validity/mode");
    Console.WriteLine($"{generator.GetType().Name} records={objs.Length} models={objs.Select(o=>o.Model.Path).Distinct().Count()} mode={expect}");allObjects.AddRange(objs);
   }
   var sorted=allObjects.OrderBy(o=>o.Model.Path,StringComparer.Ordinal).ThenBy(o=>o.Point.X).ThenBy(o=>o.Point.Y).ThenBy(o=>o.Yaw).ToArray();
   Check(sorted.Select(o=>o.ToTerrainBuilderCSV()).Distinct().Count()==sorted.Length,"exact duplicates");
   var keys=sorted.Select(o=>FormattableString.Invariant($"{o.Model.Path};{o.Point.X:R};{o.Point.Y:R};{o.Yaw:R};{o.Pitch:R};{o.Roll:R};{o.Scale:R}")).ToArray();
   var z=sorted.Select(o=>o.ToWrpTransform(grid).M42).ToArray();Check(z.All(float.IsFinite),"z finite");
   Check(NodeInput.GridHash(grid)==input.Fingerprint,"grid mutation");Check(roadBefore==string.Join("\n",roads.Select(RoadKey).Order())&&railBefore==string.Join("\n",rails.Select(RailKey).Order()),"geometry mutated");
   Console.WriteLine($"delta={delta} roads={roads.Count} rail_segments={rails.Count} roundtrip={round.Roads.Count} profiles={round.RoadTypeInfos.Count} records={sorted.Length} road_fingerprint={fileFingerprint} grid={input.Fingerprint}");
   return (roadBefore,railBefore,fileFingerprint,keys,z,sorted.Select(o=>o.Elevation).ToArray(),sorted.Select(o=>(int)o.ElevationMode).ToArray());
  }finally{ctx.DisposeHugeImages();}
 }
 var missing=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),new[]{typeof(RailwaysData)}),new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
 try{await Reject(async()=>{await missing.GetDataAsync<RailwaysData>();},"RoadsData");await Reject(async()=>{await missing.GetDataAsync<ElevationData>();},"ElevationData");}finally{missing.DisposeHugeImages();}
 Console.WriteLine("MISSING_DEPENDENCIES_REFUSED PASS");
 var a=await Run(0);var b=await Run(0);var c=await Run(100);
 Check(a.roads==b.roads&&a.roads==c.roads&&a.rails==b.rails&&a.rails==c.rails&&a.files==b.files&&a.files==c.files,"road/rail repeat");
 Check(a.objects.SequenceEqual(b.objects)&&a.z.SequenceEqual(b.z)&&a.absolute.SequenceEqual(b.absolute)&&a.modes.SequenceEqual(b.modes),"repeat");
 Check(a.objects.SequenceEqual(c.objects)&&a.modes.SequenceEqual(c.modes)&&a.z.Zip(c.z,(x,y)=>Math.Abs(y-x-100)<0.001f).All(x=>x),"+100m shift");
 Check(a.absolute.Zip(c.absolute,(x,y)=>y-x).Zip(a.modes,(dz,m)=>Math.Abs(dz-(m==(int)ElevationMode.Absolute?100:0))<0.001f).All(x=>x),"mode shift");
 Check(Hash(Encoding.UTF8.GetBytes(xml))==xmlHash&&Hash(File.ReadAllBytes(args[0]))==Hash(config)&&Hash(File.ReadAllBytes(args[1]))==Hash(cache),"source mutation");
 Console.WriteLine("PASS synthetic native roads compiler/reader, railway and bridge; +100m Z, repeat, unchanged grids; no physical fit proof");return 0;

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
sealed class ReviewFileSystem:IGameFileSystemWriter {
 public string Prefix{get;} public Dictionary<string,byte[]> Files{get;}=new(StringComparer.Ordinal);
 public ReviewFileSystem(string prefix){Prefix=prefix;}
 void CheckPath(string path){if(!new[]{"roads.shp","roads.shx","roads.dbf","roadslib.cfg"}.Any(n=>path==Prefix+"\\"+n))throw new InvalidOperationException("unreviewed write/read "+path);}
 public void CreateDirectory(string path){if(path!=Prefix)throw new InvalidOperationException("unreviewed directory");}
 public void WriteTextFile(string path,string text){CheckPath(path);Files[path]=Encoding.UTF8.GetBytes(text);}
 public Stream Create(string path){CheckPath(path);return new CapturedStream(bytes=>Files[path]=bytes);}
 public bool FileExists(string path){CheckPath(path);return Files.ContainsKey(path);}
 public Stream? OpenFileIfExists(string path){CheckPath(path);return Files.TryGetValue(path,out var bytes)?new MemoryStream(bytes,false):null;}
 public IEnumerable<string> FindAll(string pattern)=>throw new NotSupportedException();
 public DateTime? GetLastWriteTimeUtc(string path)=>throw new NotSupportedException();
 public string? GetLocationInfoForError(string path)=>null;
 public void WritePngImage(string path,SixLabors.ImageSharp.Image image)=>throw new NotSupportedException();
 sealed class CapturedStream(Action<byte[]> save):MemoryStream {protected override void Dispose(bool disposing){if(disposing&&CanRead)save(ToArray());base.Dispose(disposing);}}
}
