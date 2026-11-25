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

 var map=new Arma3MapConfig(new Arma3MapConfigJson {Center="9 N, 33 E",GridSize=16,GridCellSize=30,WorldName="synthetic_only",TargetModDirectory="unused",TileSize=512});
 var area=map.TerrainArea;

 var reviewed=new[]{typeof(RoadsData),typeof(RailwaysData),typeof(LakesData),typeof(WatercoursesData),typeof(WatercourseRadialData),typeof(SandSurfacesData),typeof(OceanData),typeof(CoastlineData),typeof(ConditionEvaluator),typeof(BuildingsData),typeof(CategoryAreaData),typeof(CitiesData)};
 string Tag(string k,string v)=>$"<tag k=\"{k}\" v=\"{v}\"/>";
 string Node(int id,float x,float y,string tags="") {var c=area.TerrainPointToLatLng(new TerrainPoint(x,y));return FormattableString.Invariant($"<node id=\"{id}\" lat=\"{c.Y:R}\" lon=\"{c.X:R}\">{tags}</node>");}
 string Way(int id,int[] nodes,string tags)=>$"<way id=\"{id}\">"+string.Concat(nodes.Select(n=>$"<nd ref=\"{n}\"/>"))+tags+"</way>";
 string Rect(int id,int w,float x,float y,float X,float Y,string tags)=>Node(id,x,y)+Node(id+1,X,y)+Node(id+2,X,Y)+Node(id+3,x,Y)+Way(w,new[]{id,id+1,id+2,id+3,id},tags);
 var xml="<osm version=\"0.6\">"+Rect(1,101,180,180,300,300,Tag("natural","water")+Tag("water","lake"))
 +Rect(5,102,0,350,60,430,Tag("natural","water")+Tag("water","pond"))
 +Rect(9,103,340,310,420,390,Tag("natural","sand"))
 +Node(13,60,240)+Node(14,420,240)+Way(104,new[]{13,14},Tag("waterway","river")+Tag("width","24"))
 +Node(15,80,60)+Node(16,80,160)+Way(105,new[]{15,16},Tag("waterway","stream")+Tag("tunnel","yes"))
 +Node(17,120,60)+Node(18,120,160)+Way(106,new[]{17,18},Tag("waterway","canal"))
 +Node(19,360,60)+Node(20,360,300)+Way(107,new[]{19,20},Tag("highway","residential"))+"</osm>";
 var xmlHash=Hash(Encoding.UTF8.GetBytes(xml));
 bool Inside(IEnumerable<TerrainPolygon> polys,float x,float y)=>polys.Any(p=>p.Contains(new TerrainPoint(x,y)));
 var lib=assets.Materials;
 var defs=lib.Definitions.SelectMany(d=>d.Usages.Select(u=>(u,d.Material))).ToDictionary(x=>x.u,x=>x.Material);
 Check(defs.Count==16&&lib.Definitions.Select(d=>d.Material.Id).Distinct().Count()==11,"material identity");
 foreach(var (usage,mat) in defs)Check(ReferenceEquals(lib.GetMaterialByUsage(usage),mat)&&ReferenceEquals(lib.GetMaterialById(mat.Id),mat),"native material mapping");
 Console.WriteLine("MATERIAL_IDS PASS usages=16 colors=11 missing_surface="+lib.Definitions.Count(d=>d.Surface==null));
 async Task<(string mask,string geometry,string[] records,float[] z)> Run(int delta){
  var rows=Enumerable.Range(0,16).Select(y=>string.Join(" ",Enumerable.Range(0,16).Select(x=>100+x+2*(15-y)+delta)));
  var asc=Encoding.ASCII.GetBytes("ncols 16\nnrows 16\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n"+string.Join("\n",rows)+"\n");
  var prj=Encoding.ASCII.GetBytes("synthetic fixture only");
  var input=NodeInput.Parse(asc,prj,new NodeContract(16,30,1000,2000,"EPSG:32636","EGM2008","m",Hash(asc),Hash(prj),"synthetic fixture only"));
  var grid=input.CopyGrid();var ctx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
  try{
   ctx.SetData(new ElevationData(grid));
   var lake=await ctx.GetDataAsync<LakesData>();var water=await ctx.GetDataAsync<WatercoursesData>();var sand=await ctx.GetDataAsync<SandSurfacesData>();var roads=await ctx.GetDataAsync<RoadsData>();
   var ocean=await ctx.GetDataAsync<OceanData>();var coast=await ctx.GetDataAsync<CoastlineData>();
   Check(lake.Polygons.Count==2&&sand.Polygons.Count==1&&roads.Roads.Count==1&&ocean.Polygons.Count==0&&coast.Polygons.Count==0,"native support geometry");
   Check(Inside(lake.Polygons,240,240)&&Inside(lake.Polygons,40,390)&&!Inside(lake.Polygons,10,390),"lake interior and native edge margin");
   Console.WriteLine("PATHS "+string.Join(";",water.Paths.Select(w=>$"{w.TypeId}:{w.Width}:{w.Path.Points.Count}")));
   Check(water.Paths.Count==3&&water.Paths.Count(w=>w.TypeId==WatercourseTypeId.StreamTunnel&&!w.IsTunnel&&w.Width==0)==1&&water.Paths.Count(w=>w.TypeId==WatercourseTypeId.River&&w.Width==10)==2,"river split/width/tunnel/canal");
   Check(Inside(water.Polygons,100,240)&&Inside(water.Polygons,400,240)&&!Inside(water.Polygons,240,240)&&!Inside(water.Polygons,360,240)&&!Inside(water.Polygons,80,100)&&!Inside(water.Polygons,120,100)&&!Inside(water.Polygons,100,249),"native water mask priorities");
   bool denied=false;try{await ctx.GetDataAsync<WatercourseRadialData>();}catch(Exception ex) when(ex.GetBaseException().Message.Contains("ElevationWithLakesData")){denied=true;}Check(denied,"radial forbidden height dependency");
   // Native public polygon renderer; deliberately not the full IdMapRender. Only four fixture usages.
   using var img=new Image<Rgba32>(480,480,new Color(lib.GetMaterialByUsage(TerrainMaterialUsage.Default).Id).ToPixel<Rgba32>());
   var options=new DrawingOptions();options.GraphicsOptions.Antialias=false;
   void Paint(IEnumerable<TerrainPolygon> polys,TerrainMaterialUsage usage)=>img.Mutate(d=>{foreach(var p in polys)PolygonDrawHelper.DrawPolygon(d,p,new SolidBrush(new Color(lib.GetMaterialByUsage(usage).Id)),options,pts=>pts.Select(p=>new PointF(p.X,480-p.Y)));});
   Paint(sand.Polygons,TerrainMaterialUsage.Sand);Paint(water.Polygons,TerrainMaterialUsage.RiverGround);Paint(lake.Polygons,TerrainMaterialUsage.LakeGround);
   void Pixel(int x,int y,TerrainMaterialUsage usage)=>Check(img[x,480-y]==new Color(lib.GetMaterialByUsage(usage).Id).ToPixel<Rgba32>(),"pixel "+x+","+y+":"+usage);
   Pixel(240,240,TerrainMaterialUsage.LakeGround);Pixel(100,240,TerrainMaterialUsage.RiverGround);Pixel(380,350,TerrainMaterialUsage.Sand);Pixel(360,240,TerrainMaterialUsage.Default);Pixel(80,100,TerrainMaterialUsage.Default);Pixel(10,390,TerrainMaterialUsage.Default);
   var bytes=new byte[480*480*4];img.CopyPixelDataTo(bytes);var unique=new HashSet<Rgba32>();for(int y=0;y<480;y++)for(int x=0;x<480;x++)unique.Add(img[x,y]);Check(unique.All(c=>lib.Definitions.Any(d=>new Color(d.Material.Id).ToPixel<Rgba32>()==c)),"unknown mask ID");
   var generator=new Arma3LayerGeneratorCatalog(assets).Generators.Single(g=>g.GetType().Name=="WatercourseGenerator");
   var records=(await generator.Generate(map,ctx,new NoProgress())).OrderBy(o=>o.ToTerrainBuilderCSV(),StringComparer.Ordinal).ToArray();
   Check(records.Length>0&&records.All(o=>o.IsValid&&o.ElevationMode==ElevationMode.Relative&&ReferenceEquals(o.Model,resolver.ResolveByPath(o.Model.Path))),"native watercourse records");
   var z=records.Select(o=>o.ToWrpTransform(grid).M42).ToArray();Check(z.All(float.IsFinite)&&NodeInput.GridHash(grid)==input.Fingerprint,"finite z/unchanged grid");
   var geometry=FormattableString.Invariant($"lake_area={lake.Polygons.Sum(p=>p.Area):F2} river_area={water.Polygons.Sum(p=>p.Area):F2} sand_area={sand.Polygons.Sum(p=>p.Area):F2}");
   Console.WriteLine($"delta={delta} {geometry} lakes={lake.Polygons.Count} paths={water.Paths.Count} mask_colors={unique.Count} mask_sha={Hash(bytes)} native_records={records.Length} radial_refused={denied} grid={input.Fingerprint}");
   return(Hash(bytes),geometry,records.Select(o=>o.ToTerrainBuilderCSV()).ToArray(),z);
  }finally{ctx.DisposeHugeImages();}
 }
 var a=await Run(0);var b=await Run(0);var c=await Run(100);
 Check(a.mask==b.mask&&a.mask==c.mask&&a.geometry==b.geometry&&a.geometry==c.geometry&&a.records.SequenceEqual(b.records)&&a.records.SequenceEqual(c.records)&&a.z.SequenceEqual(b.z)&&a.z.Zip(c.z,(x,y)=>Math.Abs(y-x-100)<0.001f).All(v=>v),"repeat or z shift");
 Check(Hash(File.ReadAllBytes(args[0]))==Hash(config)&&Hash(File.ReadAllBytes(args[1]))==Hash(cache)&&Hash(Encoding.UTF8.GetBytes(xml))==xmlHash,"source mutation");
 Console.WriteLine("PASS native hydrography, bounded native polygon mask, native watercourse placement; lake edge clip and fixed width observed; full IdMapRender NOT RUN");return 0;
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
