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
 Need(args.Length==2,"root and run name");
 var root=Path.GetFullPath(args[0]);Need(Path.GetFileName(root)=="GRMAUTO01"&&args[1] is "run1" or "run2","fixed sandbox");
 var outdir=Path.Combine(root,args[1]);Need(!Directory.Exists(outdir),"fresh output");
 var asc=Read(Path.Combine(root,"terrain.asc"),"ed061ad8db76e9341607443114d675afcc63665fdaddc1e1a92818b32e79e324");
 var prj=Read(Path.Combine(root,"terrain.prj"),"fdab6e893555dc5503ea414374724e48aa547eedf16896329215cfa07a851bfe");
 var orig=Read(Path.Combine(root,"profile-original.grma3a"),"e2c4963027c0d8da854511772c91ca23db7238feb608136c836f8e10ac58c27e");
 var cache=Read(Path.Combine(root,"modelinfo.json"),"1177ec6d4618f198bd40f79880d3434ecbd7e0b8414881e23159c3e2a4cd9e94");
 // GM samples unchanged: synthetic GRM node origin at first pixel center (+15,+15 from TB corner).
 // Datum is a synthetic-only contract label; no real datum acceptance.
 var nc=new NodeContract(64,30,294388.084m,5698137.108m,"EPSG:32636","EGM2008","m",Hash(asc),Hash(prj),"synthetic fixture only");
 var input=NodeInput.Parse(asc,prj,nc);var grid=input.CopyGrid();
 Need(grid[0,0]==113.625f&&grid[63,63]==101.8125f&&grid[0,63]==90&&grid[63,0]==125.9375f&&grid[31,32]==108,"five GM controls");
 try{NodeInput.Parse(Array.Empty<byte>(),prj,nc);throw new Exception("missing input accepted");}catch(InvalidDataException){}
 var original=JsonNode.Parse(orig)!.AsObject();
 var profile=new JsonObject{
 ["BaseWorldName"]="CAWorld",["BaseDependency"]="A3_Map_Data",
 ["Buildings"]=new JsonObject(),["Dependencies"]=new JsonArray(),
 ["ClusterCollections"]=new JsonObject{["Forest"]=new JsonArray(original["ClusterCollections"]!["Forest"]![0]!.DeepClone())},
 ["Roads"]=original["Roads"]!.DeepClone(),
 ["Materials"]=new JsonObject{["TextureSizeInMeters"]=4,["Definitions"]=new JsonArray()}
 };
 // Only one birch cluster, no additional fill, no external ice or global clutter definitions.
 var cluster=profile["ClusterCollections"]!["Forest"]![0]!["Clusters"]!.AsArray();var first=cluster[0]!.DeepClone();cluster.Clear();first["Probability"]=1;cluster.Add(first);
 foreach(var m in original["Materials"]!["Definitions"]!.AsArray()){
  var uses=m!["Usages"]!.AsArray().Select(x=>x!.GetValue<string>()).ToArray();
  if(!uses.Any(x=>x is "Default" or "ForestGround" or "LakeGround" or "Asphalt"))continue;
  var c=m.DeepClone().AsObject();c.Remove("Surface");c["Material"]!.AsObject().Remove("FakeSatPngImage");c["Material"]!.AsObject().Remove("Data");
  profile["Materials"]!["Definitions"]!.AsArray().Add(c);
 }
 var bytes=Encoding.UTF8.GetBytes(profile.ToJsonString(new JsonSerializerOptions{WriteIndented=true}));
 var paths=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
 void Collect(JsonNode? n){if(n is JsonValue v&&v.TryGetValue<string>(out var s)&&s.EndsWith(".p3d",StringComparison.OrdinalIgnoreCase))paths.Add(s);else if(n is JsonObject ob)foreach(var x in ob)Collect(x.Value);else if(n is JsonArray ar)foreach(var x in ar)Collect(x);}
 Collect(profile);Need(paths.Count==3&&paths.All(p=>p.StartsWith(@"a3\vegetation_f_enoch\tree\t_betula_pendula_",StringComparison.OrdinalIgnoreCase)),"bounded model allowlist");
 var all=JsonSerializer.Deserialize<List<ModelInfo>>(cache)!;var selected=all.Where(m=>paths.Contains(m.Path)).ToArray();Need(selected.Length==3,"model cache coverage");
 var resolver=new ReviewModels(selected);
 var assets=JsonSerializer.Deserialize<Arma3Assets>(bytes,Arma3Assets.CreateJsonSerializerOptions(resolver,false))!;
 Need(resolver.Seen.SetEquals(paths)&&assets.Materials.Definitions.Count==4&&assets.Roads.Count==9,"native profile parse");
 try{resolver.ResolveByPath("unknown.p3d");throw new Exception("unknown model accepted");}catch(InvalidOperationException){}
 // Use coordinate conversion in installed GRM; independent UTM control points checked.
 var utm=new UniversalTransverseMercator("U",36,294388.084,5698137.108);
 var coord=UniversalTransverseMercator.ConvertUTMtoLatLong(utm,new EagerLoad(false));
 var sw=FormattableString.Invariant($"{coord.Latitude.ToDouble():R}, {coord.Longitude.ToDouble():R}");
 var map=new Arma3MapConfig(new Arma3MapConfigJson{SouthWest=sw,GridSize=64,GridCellSize=30,Resolution=4,IdMapMultiplier=1,WorldName="synthetic_only",TargetModDirectory=outdir,TileSize=512});
 var area=map.TerrainArea;Need(area.GridSize==64&&area.SizeInMeters==1920,"map extent");
 foreach(var pt in new[]{new TerrainPoint(0,0),new TerrainPoint(400,200),new TerrainPoint(1890,1890)}){
  var c=area.TerrainPointToLatLng(pt);var u=new Coordinate(c.Y,c.X).UTM;
  Need(u.LongZone==36&&Math.Abs(u.Easting-(294388.084+pt.X))<0.2&&Math.Abs(u.Northing-(5698137.108+pt.Y))<0.2,"UTM coordinate control");
 }
 string Tag(string k,string v)=>$"<tag k=\"{k}\" v=\"{v}\"/>";
 string Node(int id,float x,float y){var c=area.TerrainPointToLatLng(new TerrainPoint(x,y));return FormattableString.Invariant($"<node id=\"{id}\" lat=\"{c.Y:R}\" lon=\"{c.X:R}\"/>");}
 string Way(int id,int[] ns,string tags)=>$"<way id=\"{id}\">"+string.Concat(ns.Select(n=>$"<nd ref=\"{n}\"/>"))+tags+"</way>";
 string Rect(int i,int w,float x,float y,float X,float Y,string tags)=>Node(i,x,y)+Node(i+1,X,y)+Node(i+2,X,Y)+Node(i+3,x,Y)+Way(w,new[]{i,i+1,i+2,i+3,i},tags);
 var xml="<osm version=\"0.6\">"+Rect(1,101,100,120,420,460,Tag("natural","wood"))+Rect(5,102,620,840,910,1140,Tag("natural","water")+Tag("water","lake"))+Rect(9,103,1140,240,1360,420,Tag("landuse","meadow"))+Node(13,50,290)+Node(14,480,290)+Way(104,new[]{13,14},Tag("highway","residential"))+Node(15,1000,620)+Node(16,1510,960)+Way(105,new[]{15,16},Tag("highway","primary"))+"</osm>";
 var osm=OsmDataSource.CreateFromInlineXml(xml);
 var allowed=new[]{typeof(CategoryAreaData),typeof(RoadsData),typeof(RailwaysData),typeof(BuildingsData),typeof(LakesData),typeof(OceanData),typeof(CoastlineData),typeof(ForestData),typeof(ConditionEvaluator),typeof(CitiesData)};
 var ctx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),allowed),new NoProgress(),area,osm,map,new MemoryHugeImageStorage());
 try{
  ctx.SetData(new ElevationData(grid));
  try{await ctx.GetDataAsync<RawElevationData>();throw new Exception("fallback accepted");}catch(Exception e) when(e.GetBaseException() is InvalidOperationException&&e.GetBaseException().Message.Contains("Unreviewed builder")){}
  var roads=await ctx.GetDataAsync<RoadsData>();Need(roads.Roads.Count==2,"native roads count");
  List<TerrainPolygon> ReadPoly(long id)=>osm.Ways.Where(w=>w.Id==id).SelectMany(w=>osm.Interpret(w)).SelectMany(g=>TerrainPolygon.FromGeometry(g,area.LatLngToTerrainPoint)).SelectMany(p=>p.ClippedBy(area.TerrainBounds)).ToList();
  var lake=ReadPoly(102);var protect=lake.Concat(roads.Roads.SelectMany(r=>r.ClearPolygons)).ToList();
  var forest=ReadPoly(101).SelectMany(p=>p.SubstractAll(protect)).ToList();Need(forest.Count>0,"forest geometry");ctx.SetData(new ForestData(forest));
  var objects=(await new ForestGenerator(assets).Generate(map,ctx,new NoProgress())).ToArray();Need(objects.Length>0&&objects.Length<20000,"native forest count");
  var accepted=objects.Where(o=>o.IsValid&&paths.Contains(o.Model.Path)&&o.ElevationMode==ElevationMode.Relative&&o.Point.X>=0&&o.Point.X<1890&&o.Point.Y>=0&&o.Point.Y<1890&&forest.Any(p=>p.ContainsIncludingBorder(o.Point))&&!protect.Any(p=>p.ContainsIncludingBorder(o.Point))&&float.IsFinite(o.ToWrpTransform(grid).M42)).OrderBy(o=>o.ToTerrainBuilderCSV(),StringComparer.Ordinal).ToArray();
  Need(accepted.Length>0&&accepted.Select(o=>o.ToTerrainBuilderCSV()).Distinct().Count()==accepted.Length,"valid unique placements");
  var fs=new ReviewFileSystem(map.PboPrefix+"\\data\\roads");new RoadsCompiler(new NoProgress(),fs,((IArma3RegionAssets)assets).RoadTypeLibrary).Write(map,roads.Roads);
  var round=new RoadsDeserializer(fs).Deserialize(fs.Prefix);Need(fs.Files.Count==4&&round.Roads.Count==2,"native road readback");
  var sz=map.GetIdMapSize();Need(sz.Width==480&&sz.Height==480,"mask size");
  var lib=assets.Materials;Rgba32 Col(TerrainMaterialUsage u)=>new Color(lib.GetMaterialByUsage(u).Id).ToPixel<Rgba32>();
  using var mask=new Image<Rgba32>(480,480,Col(TerrainMaterialUsage.Default));var opts=new DrawingOptions();opts.GraphicsOptions.Antialias=false;
  void Draw(IEnumerable<TerrainPolygon> p,TerrainMaterialUsage u)=>mask.Mutate(d=>{foreach(var poly in p)PolygonDrawHelper.DrawPolygon(d,poly,new SolidBrush(new Color(Col(u))),opts,pts=>map.TerrainToIdMapPixel(pts));});
  Draw(forest,TerrainMaterialUsage.ForestGround);Draw(lake,TerrainMaterialUsage.LakeGround);Draw(roads.Roads.SelectMany(r=>r.Polygons),TerrainMaterialUsage.Asphalt);
  var palette=new[]{Col(TerrainMaterialUsage.Default),Col(TerrainMaterialUsage.ForestGround),Col(TerrainMaterialUsage.LakeGround),Col(TerrainMaterialUsage.Asphalt)};
  int[] counts=new int[4];for(int y=0;y<480;y++)for(int x=0;x<480;x++){int i=Array.IndexOf(palette,mask[x,y]);Need(i>=0,"unexpected mask color");counts[i]++;}
  Need(counts.All(n=>n>0)&&mask[50,430]==palette[1]&&mask[200,230]==palette[2]&&mask[460,20]==palette[0],"mask controls");
  Need(NodeInput.GridHash(grid)==input.Fingerprint,"GM input mutation");
  Directory.CreateDirectory(outdir);File.WriteAllBytes(Path.Combine(outdir,"synthetic.grma3a"),bytes);File.WriteAllText(Path.Combine(outdir,"fixture.osm"),xml);File.WriteAllLines(Path.Combine(outdir,"relative_objects.txt"),accepted.Select(o=>o.ToTerrainBuilderCSV()));
  new TmlGenerator().WriteLibrariesTo(accepted.Select(o=>o.Model).DistinctBy(m=>m.Path).OrderBy(m=>m.Path),Path.Combine(outdir,"templates"));
  foreach(var f in fs.Files){File.WriteAllBytes(Path.Combine(outdir,Path.GetFileName(f.Key.Replace('\\','/'))),f.Value);}
  mask.SaveAsBmp(Path.Combine(outdir,"mask.bmp"));
  var manifest=new{scope="synthetic_review_only",grid=input.Fingerprint,source_asc=Hash(asc),profile=Hash(bytes),osm=Hash(Encoding.UTF8.GetBytes(xml)),origin=new[]{294388.084,5698137.108},tb_corner_offset_m=15,extent_m=1920,objects_generated=objects.Length,objects_accepted=accepted.Length,objects_held=objects.Length-accepted.Length,roads=round.Roads.Count,mask_counts=counts,model_count=accepted.Select(o=>o.Model.Path).Distinct().Count(),status="NATIVE_BOUNDED_REVIEW_ONLY"};
  File.WriteAllText(Path.Combine(outdir,"result.json"),JsonSerializer.Serialize(manifest,new JsonSerializerOptions{WriteIndented=true}));Console.WriteLine(JsonSerializer.Serialize(manifest));
  Console.WriteLine("PASS bounded native forest/roads and companion mask; missing GM, raw elevation, unknown model refused; no TB import approval");
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

