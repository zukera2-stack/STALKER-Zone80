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
 Need(args.Length==3,"root, sector W/E/REF, attempt a/b");
 var root=Path.GetFullPath(args[0]);string sector=args[1],attempt=args[2];
 Need(Path.GetFileName(root)=="GRMAUTO02" && sector is "C" && attempt is "a" or "b","fixed synthetic run");
 var outdir=Path.Combine(root,sector,attempt);Need(!Directory.Exists(outdir),"fresh output");
 var (size,ox,oy,ascHash,prjHash)=sector switch{
  "W"=>(32,180,300,"09dc163a8c50db62bb345319f7eba43b2d44535fbedc594f7c2d33698612a18e","81f38559a85a513efce9238b782ac86bd2a05694754ccb6efdd627a016f822d8"),
  "E"=>(32,780,300,"cfcbc627695e713f95fff43e5b907a8e2c3e3cb5f17f020e2b2a083b49a47326","81f38559a85a513efce9238b782ac86bd2a05694754ccb6efdd627a016f822d8"),
  "C"=>(24,600,420,"a5f14e61851795de724548869189373c7c3e5b25f7d145587c8b891d949c49d9","81f38559a85a513efce9238b782ac86bd2a05694754ccb6efdd627a016f822d8"),
  _=>(64,0,0,"ed061ad8db76e9341607443114d675afcc63665fdaddc1e1a92818b32e79e324","fdab6e893555dc5503ea414374724e48aa547eedf16896329215cfa07a851bfe")
 };
 var asc=Read(Path.Combine(root,sector,"terrain.asc"),ascHash);
 var prj=Read(Path.Combine(root,sector,"terrain.prj"),prjHash);
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
 // One shared world-coordinate OSM source, independently parsed by each context.
 string Tag(string k,string v)=>$"<tag k=\"{k}\" v=\"{v}\"/>";
 string Node(int id,float x,float y){var c=world.TerrainPointToLatLng(new TerrainPoint(x,y));return FormattableString.Invariant($"<node id=\"{id}\" lat=\"{c.Y:R}\" lon=\"{c.X:R}\"/>");}
 string Way(int id,int[] ns,string tags)=>$"<way id=\"{id}\">"+string.Concat(ns.Select(n=>$"<nd ref=\"{n}\"/>"))+tags+"</way>";
 string Rect(int i,int w,float x,float y,float X,float Y,string tags)=>Node(i,x,y)+Node(i+1,X,y)+Node(i+2,X,Y)+Node(i+3,x,Y)+Way(w,new[]{i,i+1,i+2,i+3,i},tags);
 var xml="<osm version=\"0.6\">"+Rect(1,101,800,550,1120,940,Tag("natural","wood"))+Rect(5,102,880,950,1040,1030,Tag("natural","water")+Tag("water","lake"))+Node(9,420,760)+Node(10,960,760)+Node(11,1500,760)+Way(103,new[]{9,10,11},Tag("highway","residential"))+Node(12,420,500)+Node(13,960,600)+Node(14,1500,700)+Way(104,new[]{12,13,14},Tag("highway","primary"))+"</osm>";
 var osm=OsmDataSource.CreateFromInlineXml(xml);
 var allowed=new[]{typeof(CategoryAreaData),typeof(RoadsData),typeof(RailwaysData),typeof(BuildingsData),typeof(LakesData),typeof(OceanData),typeof(CoastlineData),typeof(ForestData),typeof(ConditionEvaluator),typeof(CitiesData)};
 var ctx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),allowed),new NoProgress(),area,osm,map,new MemoryHugeImageStorage());
 try{
  ctx.SetData(new ElevationData(grid));
  try{await ctx.GetDataAsync<RawElevationData>();throw new Exception("raw fallback accepted");}catch(Exception e) when(e.GetBaseException() is InvalidOperationException&&e.GetBaseException().Message.Contains("Unreviewed builder")){}
  var roads=await ctx.GetDataAsync<RoadsData>();Need(roads.Roads.Count==2,"two native roads");
  List<TerrainPolygon> ReadPoly(long id)=>osm.Ways.Where(w=>w.Id==id).SelectMany(w=>osm.Interpret(w)).SelectMany(g=>TerrainPolygon.FromGeometry(g,area.LatLngToTerrainPoint)).SelectMany(p=>p.ClippedBy(area.TerrainBounds)).ToList();
  var lake=ReadPoly(102);var protect=lake.Concat(roads.Roads.SelectMany(r=>r.ClearPolygons)).ToList();
  var forest=ReadPoly(101).SelectMany(p=>p.SubstractAll(protect)).ToList();Need(forest.Count>0&&lake.Count>0,"forest/lake");
  ctx.SetData(new ForestData(forest));
  var objects=(await new ForestGenerator(assets).Generate(map,ctx,new NoProgress())).ToArray();Need(objects.Length>0&&objects.Length<20000,"native count");
  string Reason(TerrainBuilderObject o){
   if(!o.IsValid||!paths.Contains(o.Model.Path)||o.ElevationMode!=ElevationMode.Relative||!float.IsFinite(o.ToWrpTransform(grid).M42))return "invalid";
   if(o.Point.X<0||o.Point.X>=(size-1)*30||o.Point.Y<0||o.Point.Y>=(size-1)*30)return "extent";
   if(!forest.Any(p=>p.ContainsIncludingBorder(o.Point)))return "outside_forest";
   if(protect.Any(p=>p.ContainsIncludingBorder(o.Point)))return "protected";
   return "";
  }
  var rec=objects.Select(o=>new{model=o.Model.Name,x=(double)o.Point.X+ox,y=(double)o.Point.Y+oy,z=(double)o.ToWrpTransform(grid).M42,yaw=o.Yaw,pitch=o.Pitch,roll=o.Roll,scale=o.Scale,elevation=o.Elevation,reason=Reason(o)}).OrderBy(o=>o.x).ThenBy(o=>o.y).ThenBy(o=>o.model).ToArray();
  Need(rec.Where(o=>o.reason=="").Select(o=>(o.x,o.y)).Distinct().Count()==rec.Count(o=>o.reason==""),"exact duplicate anchors");
  var fs=new ReviewFileSystem(map.PboPrefix+"\\data\\roads");new RoadsCompiler(new NoProgress(),fs,((IArma3RegionAssets)assets).RoadTypeLibrary).Write(map,roads.Roads);
  var round=new RoadsDeserializer(fs).Deserialize(fs.Prefix);Need(fs.Files.Count==4&&round.Roads.Count==2,"native road readback");
  var sz=map.GetIdMapSize();Need(sz.Width==size*30/4&&sz.Height==sz.Width,"mask dimensions");
  var lib=assets.Materials;Rgba32 Col(TerrainMaterialUsage u)=>new Color(lib.GetMaterialByUsage(u).Id).ToPixel<Rgba32>();
  using var mask=new Image<Rgba32>(sz.Width,sz.Height,Col(TerrainMaterialUsage.Default));var opts=new DrawingOptions();opts.GraphicsOptions.Antialias=false;
  void Draw(IEnumerable<TerrainPolygon> p,TerrainMaterialUsage u)=>mask.Mutate(d=>{foreach(var poly in p)PolygonDrawHelper.DrawPolygon(d,poly,new SolidBrush(new Color(Col(u))),opts,pts=>map.TerrainToIdMapPixel(pts));});
  Draw(forest,TerrainMaterialUsage.ForestGround);Draw(lake,TerrainMaterialUsage.LakeGround);Draw(roads.Roads.SelectMany(r=>r.Polygons),TerrainMaterialUsage.Asphalt);
  var palette=new[]{Col(TerrainMaterialUsage.Default),Col(TerrainMaterialUsage.ForestGround),Col(TerrainMaterialUsage.LakeGround),Col(TerrainMaterialUsage.Asphalt)};
  int[] counts=new int[4];for(int y=0;y<mask.Height;y++)for(int x=0;x<mask.Width;x++){int i=Array.IndexOf(palette,mask[x,y]);Need(i>=0,"unknown mask color");counts[i]++;}
  Need(counts.All(n=>n>0),"all classes present");
  // Shared subcell sample points near seam, all within both node grids.
  var probes=(from y in Enumerable.Range(0,21) from x in Enumerable.Range(0,11) let X=910+x*10f let Y=480+y*29.5f select new{x=X,y=Y,z=grid.ElevationAt(new TerrainPoint(X-ox,Y-oy))}).ToArray();
  Need(probes.All(p=>float.IsFinite(p.z))&&NodeInput.GridHash(grid)==input.Fingerprint,"height probes/grid");
  Directory.CreateDirectory(outdir);
  File.WriteAllText(Path.Combine(outdir,"fixture.osm"),xml);File.WriteAllText(Path.Combine(outdir,"objects.json"),JsonSerializer.Serialize(rec));
  File.WriteAllText(Path.Combine(outdir,"heights.json"),JsonSerializer.Serialize(probes));
  foreach(var f in fs.Files)File.WriteAllBytes(Path.Combine(outdir,Path.GetFileName(f.Key.Replace('\\','/'))),f.Value);
  mask.SaveAsBmp(Path.Combine(outdir,"mask.bmp"));
  var manifest=new{scope="synthetic_seam_review_only",sector,offset=new[]{ox,oy},size,grid=input.Fingerprint,source_asc=Hash(asc),osm=Hash(Encoding.UTF8.GetBytes(xml)),objects_generated=objects.Length,objects_accepted=rec.Count(o=>o.reason==""),objects_held=rec.Count(o=>o.reason!=""),roads=round.Roads.Count,mask_counts=counts};
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

