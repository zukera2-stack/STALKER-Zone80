using System.Numerics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Security.Cryptography;
using System.Diagnostics.CodeAnalysis;
using GameRealisticMap;
using GameRealisticMap.Arma3;
using GameRealisticMap.Arma3.Assets;
using GameRealisticMap.Arma3.GameEngine;
using GameRealisticMap.Arma3.GameEngine.Roads;
using GameRealisticMap.Arma3.IO;
using GameRealisticMap.Arma3.TerrainBuilder;
using GameRealisticMap.Arma3.TerrainBuilder.TmlFiles;
using GameRealisticMap.Arma3.Nature.Forests;
using GameRealisticMap.Conditions;
using GameRealisticMap.Configuration;
using GameRealisticMap.ElevationModel;
using GameRealisticMap.Geometries;
using GameRealisticMap.ManMade;
using GameRealisticMap.ManMade.Buildings;
using GameRealisticMap.ManMade.Places;
using GameRealisticMap.ManMade.Roads;
using GameRealisticMap.ManMade.Railways;
using GameRealisticMap.Nature.Forests;
using GameRealisticMap.Nature.Lakes;
using GameRealisticMap.Nature.Ocean;
using GameRealisticMap.Osm;
using Pmad.HugeImages.Storage;
using Pmad.ProgressTracking;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Drawing.Processing;
using SixLabors.ImageSharp.Processing;
using Zone80.GmBridge;
using CoordinateSharp;
static void Need(bool b,string why){if(!b)throw new InvalidDataException(why);}
static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
static byte[] Read(string p,string h){var b=File.ReadAllBytes(p);Need(Hash(b)==h,"input digest "+Path.GetFileName(p));return b;}

try{
 Need(args.Length==2,"root and run a/b");
 var root=Path.GetFullPath(args[0]); string attempt=args[1];
 Need(Path.GetFileName(root)=="GRMAUTO04" && attempt is "c" or "d","fixed synthetic run");
 var outdir=Path.Combine(root,attempt);Need(!Directory.Exists(outdir),"fresh output");
 const int size=64,ox=0,oy=0;
 var asc=Read(Path.Combine(root,"terrain.asc"),"ed061ad8db76e9341607443114d675afcc63665fdaddc1e1a92818b32e79e324");
 var prj=Read(Path.Combine(root,"terrain.prj"),"fdab6e893555dc5503ea414374724e48aa547eedf16896329215cfa07a851bfe");
 var bytes=Read(Path.Combine(root,"synthetic.grma3a"),"4321314e74a02638a3c018d829226fdebc0c6fda0468484474d8c904b19fb039");
 var cache=Read(Path.Combine(root,"modelinfo.json"),"1177ec6d4618f198bd40f79880d3434ecbd7e0b8414881e23159c3e2a4cd9e94");
 var nc=new NodeContract(size,30,294388.084m+ox,5698137.108m+oy,"EPSG:32636","EGM2008","m",Hash(asc),Hash(prj),"synthetic fixture only");
 var input=NodeInput.Parse(asc,prj,nc);var grid=input.CopyGrid();
 // Use the exact same restricted profile from the accepted measured run.
 using var cfg=JsonDocument.Parse(bytes);
 var paths=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
 void Collect(JsonElement n){if(n.ValueKind==JsonValueKind.String&&n.GetString()!.EndsWith(".p3d",StringComparison.OrdinalIgnoreCase))paths.Add(n.GetString()!);else if(n.ValueKind==JsonValueKind.Object)foreach(var x in n.EnumerateObject())Collect(x.Value);else if(n.ValueKind==JsonValueKind.Array)foreach(var x in n.EnumerateArray())Collect(x);}
 Collect(cfg.RootElement);Need(paths.Count==3&&paths.All(p=>p.StartsWith(@"a3\vegetation_f_enoch\tree\t_betula_pendula_",StringComparison.OrdinalIgnoreCase)),"bounded model allowlist");
 var all=JsonSerializer.Deserialize<List<ModelInfo>>(cache)!;var selected=all.Where(m=>paths.Contains(m.Path)).ToArray();Need(selected.Length==3,"model cache coverage");
 var resolver=new ReviewModels(selected);
 var assets=JsonSerializer.Deserialize<Arma3Assets>(bytes,Arma3Assets.CreateJsonSerializerOptions(resolver,false))!;
 Need(resolver.Seen.SetEquals(paths)&&assets.Materials.Definitions.Count==4&&assets.Roads.Count==9,"profile");
 Arma3MapConfig Map(int n,int x,int y){
  var utm=new UniversalTransverseMercator("U",36,294388.084+x,5698137.108+y);
  var c=UniversalTransverseMercator.ConvertUTMtoLatLong(utm,new EagerLoad(false));
  var sw=FormattableString.Invariant($"{c.Latitude.ToDouble():R}, {c.Longitude.ToDouble():R}");
  return new Arma3MapConfig(new Arma3MapConfigJson{SouthWest=sw,GridSize=n,GridCellSize=30,Resolution=4,IdMapMultiplier=1,WorldName="synthetic_only",TargetModDirectory=outdir,TileSize=512});
 }
 var world=Map(64,0,0).TerrainArea;
 var map=Map(size,ox,oy);var area=map.TerrainArea;
 Need(area.GridSize==size&&area.SizeInMeters==size*30,"area extent");
 var xml=Encoding.UTF8.GetString(Read(Path.Combine(root,"fixture.osm"),"86a6b53a1ff56f992bc8ea7bd590058daba8869e3983dbb332467a85cfb17ce3"));
 var osm=OsmDataSource.CreateFromInlineXml(xml);
 var allowed=new[]{typeof(CategoryAreaData),typeof(RoadsData),typeof(RailwaysData),typeof(BuildingsData),typeof(LakesData),typeof(OceanData),typeof(CoastlineData),typeof(ForestData),typeof(ConditionEvaluator),typeof(CitiesData)};
 var ctx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),allowed),new NoProgress(),area,osm,map,new MemoryHugeImageStorage());
 try{
  ctx.SetData(new ElevationData(grid));
  try{await ctx.GetDataAsync<RawElevationData>();throw new Exception("raw fallback accepted");}catch(Exception e) when(e.GetBaseException() is InvalidOperationException&&e.GetBaseException().Message.Contains("Unreviewed builder")){}
  var roads=await ctx.GetDataAsync<RoadsData>();Need(roads.Roads.Count==2,"two native roads");
  List<TerrainPolygon> ReadPoly(long id)=>osm.Ways.Where(w=>w.Id==id).SelectMany(w=>osm.Interpret(w)).SelectMany(g=>TerrainPolygon.FromGeometry(g,area.LatLngToTerrainPoint)).SelectMany(p=>p.ClippedBy(area.TerrainBounds)).ToList();
  var lake=ReadPoly(102);var protect=lake.Concat(roads.Roads.SelectMany(r=>r.ClearPolygons)).ToList();
  var forest=ReadPoly(101).Concat(ReadPoly(105)).SelectMany(p=>p.SubstractAll(protect)).ToList();Need(forest.Count>0,"forest");
  ctx.SetData(new ForestData(forest));
  // Preserve retained native placements. Validate against canonical geometry; do not generate replacements.
  using var previous=JsonDocument.Parse(Read(Path.Combine(root,"retained","MANIFEST.json"),"49cc261ed8fc5da6c17945886a4d0ffe53752b4264efeccf4b1cbb64123a2368"));
  var hashes=previous.RootElement.GetProperty("files");
  var kept=new List<(string id,TerrainBuilderObject obj,double x,double y)>();var holds=new List<object>();var seen=new HashSet<string>();
  double maxz=0;int inputCount=0;
  foreach(string sector in new[]{"SW","SE","NW","NE"}){
   string n=sector+"_objects.json";using var doc=JsonDocument.Parse(Read(Path.Combine(root,"retained",n),hashes.GetProperty(n).GetString()!));
   foreach(var v in doc.RootElement.EnumerateArray()){
    inputCount++;string id=v.GetProperty("id").GetString()!;Need(seen.Add(id),"duplicate ID");
    float F(string k)=>v.GetProperty(k).GetSingle();
    var point=new TerrainPoint(F("x"),F("y"));Need(point.X>=480&&point.X<1440&&point.Y>=480&&point.Y<1440,"extent");
    var model=resolver.ResolveByName(v.GetProperty("model").GetString()!);
    var native=new TerrainBuilderObject(model,point,F("elevation"),ElevationMode.Relative,F("yaw"),F("pitch"),F("roll"),F("scale"));
    double dz=Math.Abs(native.ToWrpTransform(grid).M42-v.GetProperty("z").GetDouble());Need(dz<0.001,"height transform");maxz=Math.Max(maxz,dz);
    string reason=!native.IsValid?"invalid":!forest.Any(p=>p.ContainsIncludingBorder(point))?"outside_canonical_forest":protect.Any(p=>p.ContainsIncludingBorder(point))?"canonical_protected":"";
    if(reason!=""){holds.Add(new{id,reason});continue;}
    var tb=new TerrainBuilderObject(model,new TerrainPoint(point.X+15,point.Y+15),native.Elevation,native.ElevationMode,native.Yaw,native.Pitch,native.Roll,native.Scale);
    kept.Add((id,tb,v.GetProperty("x").GetDouble(),v.GetProperty("y").GetDouble()));
   }
  }
  Need(inputCount==4562&&kept.Count+holds.Count==inputCount&&kept.Count>0,"placement conservation");
  Need(kept.Select(o=>o.obj.ToTerrainBuilderCSV()).Distinct().Count()==kept.Count,"duplicate CSV");
  var fs=new ReviewFileSystem(map.PboPrefix+"\\data\\roads");new RoadsCompiler(new NoProgress(),fs,((IArma3RegionAssets)assets).RoadTypeLibrary).Write(map,roads.Roads);
  var round=new RoadsDeserializer(fs).Deserialize(fs.Prefix);Need(fs.Files.Count==4&&round.Roads.Count==2,"native road readback");
  var sz=map.GetIdMapSize();Need(sz.Width==size*30/4&&sz.Height==sz.Width,"mask dimensions");
  var lib=assets.Materials;Rgba32 Col(TerrainMaterialUsage u)=>new Color(lib.GetMaterialByUsage(u).Id).ToPixel<Rgba32>();
  var palette=new[]{Col(TerrainMaterialUsage.Default),Col(TerrainMaterialUsage.ForestGround),Col(TerrainMaterialUsage.LakeGround),Col(TerrainMaterialUsage.Asphalt)};
  var roadPolygons=roads.Roads.SelectMany(r=>r.Polygons).ToArray();
  // One fixed grid; explicit inverse translation for TB. Use native polygon containment at exact pixel centers.
  using var mask=new Image<Rgba32>(480,480);using var tbmask=new Image<Rgba32>(480,480);
  int[] counts=new int[4],tbcounts=new int[4];
  int At(float x,float y){var pt=new TerrainPoint(x,y);if(roadPolygons.Any(p=>p.ContainsIncludingBorder(pt)))return 3;if(lake.Any(p=>p.ContainsIncludingBorder(pt)))return 2;if(forest.Any(p=>p.ContainsIncludingBorder(pt)))return 1;return 0;}
  for(int y=0;y<480;y++)for(int x=0;x<480;x++){
   float X=x*4+2,Y=(479-y)*4+2;
   int i=At(X,Y),j=At(X-15,Y-15);mask[x,y]=palette[i];tbmask[x,y]=palette[j];counts[i]++;tbcounts[j]++;
  }
  Need(counts.All(n=>n>0)&&tbcounts.All(n=>n>0)&&NodeInput.GridHash(grid)==input.Fingerprint,"mask/grid");
  Directory.CreateDirectory(outdir);
  foreach(var f in fs.Files)File.WriteAllBytes(Path.Combine(outdir,Path.GetFileName(f.Key.Replace('\\','/'))),f.Value);
  mask.SaveAsBmp(Path.Combine(outdir,"mask.bmp"));tbmask.SaveAsBmp(Path.Combine(outdir,"tb_mask.bmp"));
  var sorted=kept.OrderBy(o=>o.id,StringComparer.Ordinal).ToArray();
  File.WriteAllLines(Path.Combine(outdir,"relative_objects.txt"),sorted.Select(o=>{
   var fields=o.obj.ToTerrainBuilderCSV().Split(';');Need(fields.Length==9&&fields[8]=="","native CSV schema");
   fields[1]=(200015d+o.x).ToString("F3",System.Globalization.CultureInfo.InvariantCulture);
   fields[2]=(15d+o.y).ToString("F3",System.Globalization.CultureInfo.InvariantCulture);
   return string.Join(";",fields);
  }));
  File.WriteAllText(Path.Combine(outdir,"placement_ids.json"),JsonSerializer.Serialize(sorted.Select(o=>o.id)));
  File.WriteAllText(Path.Combine(outdir,"canonical_holds.json"),JsonSerializer.Serialize(holds));
  new TmlGenerator().WriteLibrariesTo(sorted.Select(o=>o.obj.Model).DistinctBy(m=>m.Path).OrderBy(m=>m.Path),Path.Combine(outdir,"templates"));
  var manifest=new{scope="synthetic_canonical_export",source_asc=Hash(asc),osm=Hash(Encoding.UTF8.GetBytes(xml)),grid=input.Fingerprint,inputCount,exported=kept.Count,held=holds.Count,max_height_delta_m=maxz,roads=round.Roads.Count,mask_counts=counts,tb_mask_counts=tbcounts};
  File.WriteAllText(Path.Combine(outdir,"result.json"),JsonSerializer.Serialize(manifest,new JsonSerializerOptions{WriteIndented=true}));Console.WriteLine(JsonSerializer.Serialize(manifest));
 }finally{ctx.DisposeHugeImages();}
 return 0;
}catch(Exception e){Console.Error.WriteLine(e);return 2;}
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

