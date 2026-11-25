using GameRealisticMap.ManMade.Airports;
using GameRealisticMap.ManMade.Surfaces;
using GameRealisticMap.Nature.Watercourses;
using GameRealisticMap.Nature.Surfaces;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Drawing.Processing;
using SixLabors.ImageSharp.Processing;
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

 var map=new Arma3MapConfig(new Arma3MapConfigJson {Center="9 N, 33 E",GridSize=16,GridCellSize=30,Resolution=1,IdMapMultiplier=1,WorldName="synthetic_only",TargetModDirectory="unused",TileSize=512});
 var area=map.TerrainArea; var lib=assets.Materials;
 var defs=lib.Definitions.SelectMany(d=>d.Usages.Select(u=>(u,d.Material))).ToDictionary(x=>x.u,x=>x.Material);
 Check(defs.Count==16&&lib.Definitions.Select(d=>d.Material.Id).Distinct().Count()==11,"material identity");
 foreach(var (usage,mat) in defs)Check(ReferenceEquals(lib.GetMaterialByUsage(usage),mat)&&ReferenceEquals(lib.GetMaterialById(mat.Id),mat),"native material mapping");
 string Tag(string k,string v)=>$"<tag k=\"{k}\" v=\"{v}\"/>";
 string Node(int id,float x,float y) {var c=area.TerrainPointToLatLng(new TerrainPoint(x,y));return FormattableString.Invariant($"<node id=\"{id}\" lat=\"{c.Y:R}\" lon=\"{c.X:R}\"/>");}
 string Way(int id,int[] nodes,string tags)=>$"<way id=\"{id}\">"+string.Concat(nodes.Select(n=>$"<nd ref=\"{n}\"/>"))+tags+"</way>";
 string Rect(int id,int w,float x,float y,float X,float Y,string tags)=>Node(id,x,y)+Node(id+1,X,y)+Node(id+2,X,Y)+Node(id+3,x,Y)+Way(w,new[]{id,id+1,id+2,id+3,id},tags);
 // Every polygon is an explicit synthetic fixture. No assumption about absence in real OSM.
 var xml="<osm version=\"0.6\">"+Rect(1,101,20,20,220,220,Tag("landuse","residential"))
 +Rect(5,102,260,20,440,150,Tag("landuse","industrial"))
 +Rect(9,103,80,80,200,200,Tag("natural","wood"))
 +Rect(13,104,40,260,150,400,Tag("landuse","meadow"))
 +Rect(17,105,110,300,250,440,Tag("landuse","farmland"))
 +Rect(21,106,280,180,420,280,Tag("landuse","grass"))
 +Rect(25,107,320,310,440,430,Tag("natural","water")+Tag("water","lake"))
 +Rect(29,108,290,300,380,380,Tag("natural","sand"))
 +Rect(33,109,130,130,240,170,Tag("surface","asphalt"))
 +Rect(37,110,30,410,70,450,Tag("landuse","orchard"))
 +Rect(41,111,80,410,105,450,Tag("landuse","vineyard"))
 +Rect(45,112,250,300,290,340,Tag("natural","bare_rock"))
 +Rect(49,113,260,330,310,365,Tag("natural","scree"))
 +Node(53,280,400)+Node(54,460,400)+Way(114,new[]{53,54},Tag("waterway","river"))
 +Node(55,20,240)+Node(56,460,240)+Way(115,new[]{55,56},Tag("highway","residential"))+"</osm>";
 var xmlHash=Hash(Encoding.UTF8.GetBytes(xml));
 var reviewed=new[]{typeof(CategoryAreaData),typeof(RoadsData),typeof(RailwaysData),typeof(BuildingsData),typeof(LakesData),typeof(WatercoursesData),typeof(SandSurfacesData),typeof(OceanData),typeof(CoastlineData),typeof(CutlinesData),typeof(ForestData),typeof(AsphaltData),typeof(AirportData),typeof(AerowaysData),typeof(GrassData)};
 async Task<string[]> Run(int delta){
  var rows=Enumerable.Range(0,16).Select(y=>string.Join(" ",Enumerable.Range(0,16).Select(x=>100+x+2*(15-y)+delta)));
  var asc=Encoding.ASCII.GetBytes("ncols 16\nnrows 16\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n"+string.Join("\n",rows)+"\n");var prj=Encoding.ASCII.GetBytes("synthetic fixture only");
  var input=NodeInput.Parse(asc,prj,new NodeContract(16,30,1000,2000,"EPSG:32636","EGM2008","m",Hash(asc),Hash(prj),"synthetic fixture only"));
  var grid=input.CopyGrid();var osm=OsmDataSource.CreateFromInlineXml(xml);var ctx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,osm,map,new MemoryHugeImageStorage());
  try{
   ctx.SetData(new ElevationData(grid));
   async Task Denied<T>() where T:class {try{await ctx.GetDataAsync<T>();}catch(Exception ex) when(ex.GetBaseException().Message.Contains("ElevationWithLakesData")){return;}throw new Exception("expected lake-height dependency refusal: "+typeof(T).Name);}
   await Denied<GrassData>();await Denied<ForestData>();
   var categories=await ctx.GetDataAsync<CategoryAreaData>();var roads=await ctx.GetDataAsync<RoadsData>();var rails=await ctx.GetDataAsync<RailwaysData>();var buildings=await ctx.GetDataAsync<BuildingsData>();var lakes=await ctx.GetDataAsync<LakesData>();var water=await ctx.GetDataAsync<WatercoursesData>();var sand=await ctx.GetDataAsync<SandSurfacesData>();var ocean=await ctx.GetDataAsync<OceanData>();var coast=await ctx.GetDataAsync<CoastlineData>();var cuts=await ctx.GetDataAsync<CutlinesData>();
   Check(categories.Areas.Count==2&&roads.Roads.Count==1&&rails.Railways.Count==0&&buildings.Buildings.Count==0&&lakes.Polygons.Count==1&&sand.Polygons.Count==1&&ocean.Polygons.Count==0&&coast.Polygons.Count==0&&cuts.Polygons.Count==0,"fixture support");
   var ids=osm.Ways.Select(w=>w.Id!.Value).ToHashSet();Check(ids.SetEquals(Enumerable.Range(101,15).Select(i=>(long)i)),"unreviewed source feature");
   List<TerrainPolygon> Read(long id)=>osm.Ways.Where(w=>w.Id==id).SelectMany(w=>osm.Interpret(w)).SelectMany(g=>TerrainPolygon.FromGeometry(g,area.LatLngToTerrainPoint)).SelectMany(p=>p.ClippedBy(area.TerrainBounds)).ToList();
   List<TerrainPolygon> Minus(IEnumerable<TerrainPolygon> a,IEnumerable<TerrainPolygon> b)=>a.SelectMany(p=>p.SubstractAll(b)).ToList();
   var priority=roads.Roads.Where(r=>r.RoadType!=RoadTypeId.Trail).SelectMany(r=>r.ClearPolygons).Concat(rails.Railways.SelectMany(r=>r.ClearPolygons)).Concat(buildings.Buildings.Select(b=>b.Box.Polygon)).Concat(lakes.Polygons).ToList();
   var forest=Minus(Read(103),priority.Concat(cuts.Polygons));ctx.SetData(new ForestData(forest));
   var vineyard=Minus(Read(111),priority.Concat(forest));var orchard=Minus(Read(110),priority.Concat(forest).Concat(vineyard));
   var meadow=Minus(Read(104),priority.Concat(forest));var farm=Minus(Read(105),priority.Concat(forest).Concat(vineyard).Concat(orchard));
   var grass=Minus(Read(106),priority.Concat(forest));var rock=Minus(Read(112),priority.Concat(forest));var scree=Minus(Read(113),priority.Concat(forest).Concat(rock));
   var asphalt=await ctx.GetDataAsync<AsphaltData>(); // real stock builder excludes forest
   Check((await ctx.GetDataAsync<AerowaysData>()).Aeroways.Count()==0,"unexpected aeroway");
   bool Inside(IEnumerable<TerrainPolygon> p,float x,float y)=>p.Any(a=>a.Contains(new TerrainPoint(x,y)));
   Check(!Inside(asphalt.Polygons,160,150)&&Inside(asphalt.Polygons,220,150)&&Inside(Read(109),160,150),"stock asphalt exclusion");
   // Candidate independent material state: vegetation does not erase documented asphalt.
   var rawAsphalt=Read(109);
   Dictionary<string,SurfaceInput> Inputs(bool preserveAsphalt)=>new(){
    ["urban"]=SurfaceInput.Geometry(categories.Areas.Where(c=>c.BuildingType==BuildingTypeId.Residential).SelectMany(c=>c.PolyList)),
    ["industrial"]=SurfaceInput.Geometry(categories.Areas.Where(c=>c.BuildingType==BuildingTypeId.Industrial).SelectMany(c=>c.PolyList)),
    ["ocean"]=SurfaceInput.Absent(),["coast"]=SurfaceInput.Absent(),["orchard"]=SurfaceInput.Geometry(orchard),["vineyard"]=SurfaceInput.Geometry(vineyard),["forest"]=SurfaceInput.Geometry(forest),["meadow"]=SurfaceInput.Geometry(meadow),["farm"]=SurfaceInput.Geometry(farm),["ice"]=SurfaceInput.Absent(),["sand"]=SurfaceInput.Geometry(sand.Polygons),["grass"]=SurfaceInput.Geometry(grass),["river"]=SurfaceInput.Geometry(water.Polygons),["lake"]=SurfaceInput.Geometry(lakes.Polygons),["scree"]=SurfaceInput.Geometry(scree),["rock"]=SurfaceInput.Geometry(rock),["asphalt"]=SurfaceInput.Geometry(preserveAsphalt?rawAsphalt:asphalt.Polygons)};
   var baseline=Inputs(false);var candidate=Inputs(true);
   void Reject(Dictionary<string,SurfaceInput> bad){try{SurfacePlan.Validate(bad);throw new Exception("expected rejection");}catch(InvalidDataException){}}
   var missing=Inputs(false);missing.Remove("lake");Reject(missing);var unknown=Inputs(false);unknown["ice"]=new SurfaceInput("unknown",new());Reject(unknown);var empty=Inputs(false);empty["forest"]=SurfaceInput.Geometry(Array.Empty<TerrainPolygon>());Reject(empty);var extra=Inputs(false);extra["invalid"]=SurfaceInput.Absent();Reject(extra);
   var a=SurfacePlan.Render(map,lib,baseline);var b=SurfacePlan.Render(map,lib,candidate);
   using var aimg=a.material;using var asem=a.semantic;using var bimg=b.material;using var bsem=b.semantic;
   void Pixel(Image<Rgba32> img,int x,int y,string slot){var expected=SurfacePlan.Semantic(slot);Check(img[x,480-y]==expected,$"semantic pixel {x},{y} expected {slot} actual {img[x,480-y]}");}
   Pixel(asem,10,10,"default");Pixel(asem,30,30,"urban");Pixel(asem,300,60,"industrial");Pixel(asem,100,100,"forest");Pixel(asem,160,150,"forest");Pixel(asem,220,150,"asphalt");Pixel(asem,60,300,"meadow");Pixel(asem,130,350,"farm");Pixel(asem,350,200,"grass");Pixel(asem,300,310,"sand");Pixel(asem,350,350,"lake");Pixel(asem,300,400,"river");Pixel(asem,270,320,"rock");Pixel(asem,300,350,"scree");Pixel(asem,50,430,"orchard");Pixel(asem,90,430,"vineyard");Pixel(bsem,160,150,"asphalt");
   var palette=SurfacePlan.SemanticPalette(lib);int changed=0;var colors=new HashSet<Rgba32>();var slots=new HashSet<Rgba32>();for(int y=0;y<aimg.Height;y++)for(int x=0;x<aimg.Width;x++){var ap=aimg[x,y];var bp=bimg[x,y];colors.Add(bp);slots.Add(bsem[x,y]);if(ap!=bp)changed++;Check(palette.TryGetValue(asem[x,y],out var am)&&am==ap&&palette.TryGetValue(bsem[x,y],out var bm)&&bm==bp,"semantic/material mismatch");}
   Check(changed>0&&NodeInput.GridHash(grid)==input.Fingerprint,"material policy change/grid unchanged");
   string ImgHash(Image<Rgba32> img){var bytes=new byte[img.Width*img.Height*4];img.CopyPixelDataTo(bytes);return Hash(bytes);}
   var result=new[]{ImgHash(aimg),ImgHash(bimg),ImgHash(bsem),changed.ToString(),colors.Count.ToString(),slots.Count.ToString()};
   Console.WriteLine($"delta={delta} size={bimg.Width}x{bimg.Height} usages=16 slots=18 observed_slots={slots.Count} colors={colors.Count} changed_pixels={changed} baseline={result[0]} candidate={result[1]} semantic={result[2]} grid={input.Fingerprint}");return result;
  }finally{ctx.DisposeHugeImages();}
 }
 var a=await Run(0);var b=await Run(0);var c=await Run(100);Check(a.SequenceEqual(b)&&a.SequenceEqual(c),"repeat/height independence");
 Check(Hash(File.ReadAllBytes(args[0]))==Hash(config)&&Hash(File.ReadAllBytes(args[1]))==Hash(cache)&&Hash(Encoding.UTF8.GetBytes(xml))==xmlHash,"source mutation");
 Console.WriteLine("PASS bounded ordered surface plan; 17 semantic controls, 4 invalid input refusals per run; native asphalt forest exclusion observed; full stock IdMapRender NOT RUN; no production raster");return 0;
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
