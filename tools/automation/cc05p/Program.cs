using OsmSharp.Geo;
using GameRealisticMap.ManMade.Fences;
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
 Check(args.Length==3,"Expected v03, modelinfo and job JSON paths");
 Check(new FileInfo(args[2]).Length<=8192,"job size");
 var jobBytes=File.ReadAllBytes(args[2]); var job=JobContract.Parse(jobBytes);
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
 string Node(int id,float x,float y,string tags="") {var c=area.TerrainPointToLatLng(new TerrainPoint(x,y));return FormattableString.Invariant($"<node id=\"{id}\" lat=\"{c.Y:R}\" lon=\"{c.X:R}\">{tags}</node>");}
 string Way(int id,int[] nodes,string tags)=>$"<way id=\"{id}\">"+string.Concat(nodes.Select(n=>$"<nd ref=\"{n}\"/>"))+tags+"</way>";
 string Rect(int id,int w,float x,float y,float X,float Y,string tags)=>Node(id,x,y)+Node(id+1,X,y)+Node(id+2,X,Y)+Node(id+3,x,Y)+Way(w,new[]{id,id+1,id+2,id+3,id},tags);
 // Every polygon is an explicit synthetic fixture. No assumption about absence in real OSM.
 var xml="<osm version=\"0.6\">"+Rect(1,101,20,20,220,220,Tag("landuse","residential"))
 +Rect(5,102,260,20,440,150,Tag("landuse","industrial"))
 +Rect(9,103,80,80,200,270,Tag("natural","wood"))
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
 +Node(55,20,240)+Node(56,460,240)+Way(115,new[]{55,56},Tag("highway","residential"))
 +Rect(57,116,255,180,335,255,Tag("natural","scrub"))
 +Rect(61,117,175,180,195,200,Tag("building","yes"))
 +Node(65,260,70)+Node(66,410,70)+Way(118,new[]{65,66},Tag("highway","primary")+Tag("bridge","yes"))
 +Node(67,245,40)+Node(68,245,190)+Way(119,new[]{67,68},Tag("railway","rail"))
 +Node(69,360,210)+Node(70,360,270)+Way(120,new[]{69,70},Tag("barrier","fence"))
 +Node(71,60,350)+Node(72,230,350)+Way(121,new[]{71,72},Tag("natural","tree_row"))
 +Node(73,140,240,Tag("natural","tree"))+Node(74,30,190,Tag("natural","tree"))
 +Node(75,45,140,Tag("amenity","bench"))+Node(76,60,140,Tag("highway","street_lamp"))
 +Node(77,80,140,Tag("power","pole"))+Node(78,90,140,Tag("amenity","post_box"))
 +Node(79,400,100,Tag("barrier","gate"))+"</osm>";
 var xmlHash=Hash(Encoding.UTF8.GetBytes(xml));Check(xmlHash==JobContract.OsmHash,"fixture XML hash");
 var reviewed=new[]{typeof(CategoryAreaData),typeof(RoadsData),typeof(RailwaysData),typeof(BuildingsData),typeof(LakesData),typeof(WatercoursesData),typeof(SandSurfacesData),typeof(OceanData),typeof(CoastlineData),typeof(CutlinesData),typeof(ForestData),typeof(AsphaltData),typeof(AirportData),typeof(AerowaysData),typeof(ConditionEvaluator),typeof(CitiesData),typeof(ForestEdgeData),typeof(ForestRadialData),typeof(ScrubData),typeof(ScrubRadialData),typeof(TreesData),typeof(FencesData),typeof(OrientedObjectData),typeof(ProceduralStreetLampsData),typeof(TreeRowsData)};
 var catalog=new Arma3LayerGeneratorCatalog(assets).Generators;
 var selectedLayers=CatalogPolicy.Validate(catalog.Select(g=>g.GetType().Name));
 var generators=catalog.Where(g=>selectedLayers.Contains(g.GetType().Name)).ToArray();Check(generators.Length==selectedLayers.Count,"catalog mismatch");
 Console.WriteLine("CATALOG total="+catalog.Count+" selected="+generators.Length+" NOT_RUN="+string.Join(",",catalog.Select(g=>g.GetType().Name).Where(n=>!selectedLayers.Contains(n)).OrderBy(n=>n,StringComparer.Ordinal)));
 async Task Reject(Func<Task> action,string expected){try{await action();}catch(Exception e) when(e.GetBaseException() is InvalidOperationException && e.GetBaseException().Message.Contains(expected)){return;}throw new Exception("missing refusal "+expected);}
 var missing=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),new[]{typeof(RailwaysData)}),new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
 try{await Reject(async()=>{await missing.GetDataAsync<RailwaysData>();},"RoadsData");await Reject(async()=>{await missing.GetDataAsync<ElevationData>();},"ElevationData");}finally{missing.DisposeHugeImages();}
 Console.WriteLine("MISSING_DEPENDENCIES_REFUSED PASS");
 async Task<(string[] keys,float[] z,string mask,string road,string review,int total,int accepted,int roadPlants)> Run(string state,int delta){
  var rows=Enumerable.Range(0,16).Select(y=>string.Join(" ",Enumerable.Range(0,16).Select(x=>100+x+2*(15-y)+delta)));
  var asc=Encoding.ASCII.GetBytes("ncols 16\nnrows 16\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n"+string.Join("\n",rows)+"\n");var prj=Encoding.ASCII.GetBytes("synthetic fixture only");
  var input=NodeInput.Parse(asc,prj,new NodeContract(16,30,1000,2000,"EPSG:32636","EGM2008","m",Hash(asc),Hash(prj),"synthetic fixture only"));
  var grid=input.CopyGrid();var osm=OsmDataSource.CreateFromInlineXml(xml);var ctx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,osm,map,new MemoryHugeImageStorage());
  try{
   ctx.SetData(new ElevationData(grid));
   foreach(var expected in new[]{"RawElevationData","ElevationWithLakesData","ElevationOutOfBoundsData"}){
    if(expected=="RawElevationData")await Reject(async()=>{await ctx.GetDataAsync<RawElevationData>();},expected);
    if(expected=="ElevationWithLakesData")await Reject(async()=>{await ctx.GetDataAsync<ElevationWithLakesData>();},expected);
    if(expected=="ElevationOutOfBoundsData")await Reject(async()=>{await ctx.GetDataAsync<ElevationOutOfBoundsData>();},expected);
   }
   var categories=await ctx.GetDataAsync<CategoryAreaData>();var roads=await ctx.GetDataAsync<RoadsData>();var rails=await ctx.GetDataAsync<RailwaysData>();var buildings=await ctx.GetDataAsync<BuildingsData>();var lakes=await ctx.GetDataAsync<LakesData>();var water=await ctx.GetDataAsync<WatercoursesData>();var sand=await ctx.GetDataAsync<SandSurfacesData>();var ocean=await ctx.GetDataAsync<OceanData>();var coast=await ctx.GetDataAsync<CoastlineData>();var cuts=await ctx.GetDataAsync<CutlinesData>();
   var ids=osm.Ways.Select(w=>w.Id!.Value).ToHashSet();Check(ids.SetEquals(Enumerable.Range(101,21).Select(i=>(long)i)),"unreviewed source way");
   Check(categories.Areas.Count==2&&roads.Roads.Count==2&&rails.Railways.Count==1&&buildings.Buildings.Count==1&&lakes.Polygons.Count==1&&sand.Polygons.Count==1&&ocean.Polygons.Count==0&&coast.Polygons.Count==0&&cuts.Polygons.Count==0,"fixture support");
   List<TerrainPolygon> Read(long id)=>osm.Ways.Where(w=>w.Id==id).SelectMany(w=>osm.Interpret(w)).SelectMany(g=>TerrainPolygon.FromGeometry(g,area.LatLngToTerrainPoint)).SelectMany(p=>p.ClippedBy(area.TerrainBounds)).ToList();
   List<TerrainPolygon> Minus(IEnumerable<TerrainPolygon> a,IEnumerable<TerrainPolygon> b)=>a.SelectMany(p=>p.SubstractAll(b)).ToList();
   var street=roads.Roads.Single(r=>r.SpecialSegment!=WaySpecialSegment.Bridge);var roadPolys=street.Polygons;
   var solid=buildings.Buildings.Select(b=>b.Box.Polygon).ToList();
   var protect=lakes.Polygons.Concat(cuts.Polygons).Concat(rails.Railways.SelectMany(r=>r.ClearPolygons)).Concat(solid).Concat(ocean.Polygons).Concat(roads.Roads.Where(r=>r.SpecialSegment==WaySpecialSegment.Bridge).SelectMany(r=>r.ClearPolygons)).ToList();
   if(state!="abandoned")protect.AddRange(street.ClearPolygons);
   var priority=roads.Roads.Where(r=>r.RoadType!=RoadTypeId.Trail).SelectMany(r=>r.ClearPolygons).Concat(rails.Railways.SelectMany(r=>r.ClearPolygons)).Concat(solid).Concat(lakes.Polygons).ToList();
   var forest=Minus(Read(103),protect);var scrub=Minus(Read(116),protect.Concat(forest));
   Check(forest.Count>0&&scrub.Count>0,"vegetation geometry");ctx.SetData(new ForestData(forest));ctx.SetData(new ScrubData(scrub));
   var edge=(await ctx.GetDataAsync<ForestEdgeData>()).Polygons;
   List<TerrainPolygon> Ring(List<TerrainPolygon> source,float width,IEnumerable<TerrainPolygon> exclusion)=>TerrainPolygon.MergeAll(Minus(source.SelectMany(p=>p.OuterCrown(width)).SelectMany(p=>p.ClippedBy(area.TerrainBounds)),exclusion));
   var fr=Ring(forest,ForestRadialData.Width,protect.Concat(forest).Concat(scrub));var sr=Ring(scrub,ScrubRadialData.Width,protect.Concat(forest).Concat(scrub).Concat(fr));
   ctx.SetData(new ForestRadialData(fr));ctx.SetData(new ScrubRadialData(sr));
   // Exact synthetic observed node anchors; production source-ID-to-output mapping not implemented.
   var tagged=osm.Nodes.Where(n=>n.Tags!=null&&n.Tags.Count>0).ToArray();Check(tagged.Select(n=>n.Id!.Value).ToHashSet().SetEquals(Enumerable.Range(73,7).Select(i=>(long)i))&&osm.Relations.Count()==0,"tagged node/relation inventory");
   var anchors=tagged.Where(n=>n.Tags.GetValue("natural")=="tree").Select(n=>(id:n.Id!.Value,point:area.LatLngToTerrainPoint(n.GetCoordinate()))).OrderBy(n=>n.id).ToArray();
   Check(anchors.Length==2,"tree inventory");
   var allowedAnchors=anchors.Where(n=>!protect.Any(q=>q.ContainsIncludingBorder(n.point))).Select(n=>n.point).ToList();Check(allowedAnchors.Count==(state=="abandoned"?2:1),"tree state");ctx.SetData(new TreesData(allowedAnchors));
   var sourceTreeDecisions=string.Join(",",anchors.Select(n=>n.id+":"+(allowedAnchors.Contains(n.point)?"allow_anchor":state=="unknown"?"review_unknown":"protected_exclusion")));
   var domains=new Dictionary<string,List<TerrainPolygon>>{{"ForestGenerator",forest},{"ForestEdgeGenerator",edge},{"ForestRadialGenerator",fr},{"ScrubGenerator",scrub},{"ScrubRadialGenerator",sr}};
   var vineyard=Minus(Read(111),priority.Concat(forest));var orchard=Minus(Read(110),priority.Concat(forest).Concat(vineyard));
   var meadow=Minus(Read(104),priority.Concat(forest));var farm=Minus(Read(105),priority.Concat(forest).Concat(vineyard).Concat(orchard));
   var grass=Minus(Read(106),priority.Concat(forest));var rock=Minus(Read(112),priority.Concat(forest).Concat(scrub));var scree=Minus(Read(113),priority.Concat(forest).Concat(rock).Concat(scrub));
   var asphalt=await ctx.GetDataAsync<AsphaltData>();
   Check((await ctx.GetDataAsync<AerowaysData>()).Aeroways.Count()==0,"unexpected aeroway");
   // Preserve documented asphalt in all states for this fixture; no age-dependent material model.
   var surfaces=new Dictionary<string,SurfaceInput>{
    ["urban"]=SurfaceInput.Geometry(categories.Areas.Where(c=>c.BuildingType==BuildingTypeId.Residential).SelectMany(c=>c.PolyList)),
    ["industrial"]=SurfaceInput.Geometry(categories.Areas.Where(c=>c.BuildingType==BuildingTypeId.Industrial).SelectMany(c=>c.PolyList)),
    ["ocean"]=SurfaceInput.Absent(),["coast"]=SurfaceInput.Absent(),["orchard"]=SurfaceInput.Geometry(orchard),["vineyard"]=SurfaceInput.Geometry(vineyard),["forest"]=SurfaceInput.Geometry(forest),["meadow"]=SurfaceInput.Geometry(meadow),["farm"]=SurfaceInput.Geometry(farm),["ice"]=SurfaceInput.Absent(),["sand"]=SurfaceInput.Geometry(sand.Polygons),["grass"]=SurfaceInput.Geometry(grass),["river"]=SurfaceInput.Geometry(water.Polygons),["lake"]=SurfaceInput.Geometry(lakes.Polygons),["scree"]=SurfaceInput.Geometry(scree),["rock"]=SurfaceInput.Geometry(rock),["asphalt"]=SurfaceInput.Geometry(Read(109))};
   var images=SurfacePlan.Render(map,lib,surfaces);using var material=images.material;using var semantic=images.semantic;
   var palette=SurfacePlan.SemanticPalette(lib);for(int y=0;y<material.Height;y++)for(int x=0;x<material.Width;x++)Check(palette.TryGetValue(semantic[x,y],out var px)&&px==material[x,y],"pixel mismatch");
   Check(semantic[160,480-150]==SurfacePlan.Semantic("asphalt")&&semantic[350,480-350]==SurfacePlan.Semantic("lake"),"surface controls");
   var bytes=new byte[material.Width*material.Height*4];material.CopyPixelDataTo(bytes);var mask=Hash(bytes);
   var fs=new ReviewFileSystem(map.PboPrefix+"\\data\\roads");new RoadsCompiler(new NoProgress(),fs,((IArma3RegionAssets)assets).RoadTypeLibrary).Write(map,roads.Roads);
   var round=new RoadsDeserializer(fs).Deserialize(fs.Prefix);Check(fs.Files.Count==4&&round.RoadTypeInfos.Count==9&&round.Roads.Count==1,"road roundtrip");
   var roadHash=Hash(Encoding.UTF8.GetBytes(string.Join("\n",round.Roads.Select(r=>r.RoadTypeInfos.Id+":"+r.Order+":"+string.Join(";",r.Path.Points.Select(p=>FormattableString.Invariant($"{p.X:R},{p.Y:R}")))).Order())+"\n"+Encoding.UTF8.GetString(fs.Files[fs.Prefix+"\\roadslib.cfg"])));
   var output=new List<(string layer,TerrainBuilderObject o)>();
   foreach(var g in generators){var name=g.GetType().Name;var objects=(await g.Generate(map,ctx,new NoProgress())).ToArray();Check(name=="SidewalksGenerator"?objects.Length==0:objects.Length>0,"unexpected layer count "+name);
    Check(objects.All(o=>o.IsValid&&requested.Contains(o.Model.Path)&&ReferenceEquals(o.Model,resolver.ResolveByPath(o.Model.Path))&&float.IsFinite(o.ToWrpTransform(grid).M42)),"invalid object "+name);
    output.AddRange(objects.Select(o=>(name,o)));Console.WriteLine($"{state} delta={delta} {name} records={objects.Length}");}
   var dup=output.GroupBy(t=>t.o.ToTerrainBuilderCSV(),StringComparer.Ordinal).Where(g=>g.Count()>1).Select(g=>g.Key).ToHashSet(StringComparer.Ordinal);
   bool Plant(string n)=>domains.ContainsKey(n)||n=="TreesGenerator"||n=="TreeRowsGenerator";
   bool InRoad(TerrainBuilderObject o)=>roadPolys.Any(p=>p.ContainsIncludingBorder(o.Point));
   string Reasons(string layer,TerrainBuilderObject o){var r=new List<string>();if(o.Point.X<0||o.Point.X>=480||o.Point.Y<0||o.Point.Y>=480)r.Add("extent");if(dup.Contains(o.ToTerrainBuilderCSV()))r.Add("duplicate_csv");if(domains.TryGetValue(layer,out var domain)&&!domain.Any(p=>p.ContainsIncludingBorder(o.Point)))r.Add("outside_layer_domain");if(Plant(layer)&&protect.Any(p=>p.ContainsIncludingBorder(o.Point)))r.Add("protected_vegetation");if(layer=="FenceGenerator"&&InRoad(o))r.Add("fence_road_review");if(solid.Any(p=>p.ContainsIncludingBorder(o.Point)))r.Add("building_footprint_review");return string.Join(",",r);}
   string Key(string layer,TerrainBuilderObject o)=>FormattableString.Invariant($"{layer};{o.Model.Path};{o.Point.X:R};{o.Point.Y:R};{o.Yaw:R};{o.Pitch:R};{o.Roll:R};{o.Scale:R};{o.ElevationMode}");
   var evaluated=output.Select(t=>(key:Key(t.layer,t.o),t.o,reason:Reasons(t.layer,t.o),t.layer)).OrderBy(t=>t.key,StringComparer.Ordinal).ToArray();
   Check(evaluated.Select(t=>t.key).Distinct(StringComparer.Ordinal).Count()==evaluated.Length,"ambiguous logical placement identity");
   var entries=evaluated.Select(t=>{
    var id=JobContract.Hash("cc05p-placement-v1\n"+JobContract.Fixture+"\n"+t.key);
    var payload=FormattableString.Invariant($"{t.key};{t.o.Elevation:R};{t.o.ToWrpTransform(grid).M42:R}");
    return new {id,key=t.key,content=JobContract.Hash(payload),payload,layer=t.layer,reason=t.reason,sector=t.reason!=""?"held":t.o.Point.X<240?"left":"right",source_feature_id=(string?)null,provenance="layer_and_fixture_only"};
   }).OrderBy(t=>t.id,StringComparer.Ordinal).ToArray();
   var pointPass=evaluated.Where(t=>t.reason=="").ToArray();var held=evaluated.Where(t=>t.reason!="").ToArray();
   var left=pointPass.Where(t=>t.o.Point.X<240).ToArray();var right=pointPass.Where(t=>t.o.Point.X>=240).ToArray();
   Check(left.Length+right.Length+held.Length==output.Count&&left.Concat(right).Select(t=>t.key).OrderBy(x=>x,StringComparer.Ordinal).SequenceEqual(pointPass.Select(t=>t.key)),"ownership reconciliation");
   var roadPlants=pointPass.Count(t=>Plant(t.layer)&&InRoad(t.o));Check(state=="abandoned"?roadPlants>0:roadPlants==0,"protected road vegetation");
   var provenance="fixture_way_ids="+string.Join(",",ids.Order())+"; tagged_node_ids="+string.Join(",",tagged.Select(n=>n.Id!.Value).Order())+"; state_way115="+state+"; tree_anchor_decisions="+sourceTreeDecisions+"; power_pole=unsupported;postbox=unconfigured;gate=unsupported;building=ZPB_pending";
   Console.WriteLine("SOURCE_REVIEW "+provenance);
   var manifest=Hash(Encoding.UTF8.GetBytes(provenance+"\n"+string.Join("\n",evaluated.Select(t=>t.key+"|"+t.reason+"|"+(t.reason!=""?"held":t.o.Point.X<240?"left":"right")))));
   Check(NodeInput.GridHash(grid)==input.Fingerprint,"height mutation");
   Console.WriteLine($"{state} delta={delta} total={output.Count} review={held.Length} left={left.Length} right={right.Length} point_pass_road_plants={roadPlants} duplicate_csv_groups={dup.Count} roads={round.Roads.Count} mask={mask} road={roadHash} review_manifest={manifest} grid={input.Fingerprint}");
   var nature=output.Where(t=>Plant(t.layer)).Select(t=>t.o.Model.Path.ToLowerInvariant()).ToArray();
   Console.WriteLine($"nature_name_candidates fallen={nature.Count(p=>p.Contains("fallen"))} stump={nature.Count(p=>p.Contains("stump"))} stem={nature.Count(p=>p.Contains("_stem"))} bush_folder={nature.Count(p=>p.Contains("\\bush\\"))} (filename heuristics only)");
   Console.WriteLine("review_reasons="+string.Join(",",held.SelectMany(t=>t.reason.Split(',')).GroupBy(r=>r).OrderBy(g=>g.Key).Select(g=>g.Key+":"+g.Count())));
   Check(Hash(File.ReadAllBytes(args[0]))==Hash(config)&&Hash(File.ReadAllBytes(args[1]))==Hash(cache)&&Hash(File.ReadAllBytes(args[2]))==Hash(jobBytes)&&Hash(Encoding.UTF8.GetBytes(xml))==xmlHash,"source mutation");
   Console.WriteLine("RESULT_JSON "+JsonSerializer.Serialize(new {schema_version=1,scope="synthetic_review_only",job_id=job.Id,fixture=JobContract.Fixture,road_state=state,height_delta_m=delta,config_sha256=Hash(config),cache_sha256=Hash(cache),osm_sha256=xmlHash,grid_sha256=input.Fingerprint,mask_sha256=mask,road_sha256=roadHash,review_sha256=manifest,catalog=CatalogPolicy.Entries,source_review=provenance,total=output.Count,held=held.Length,left=left.Length,right=right.Length,point_pass_road_plants=roadPlants,export_authorized=false,records=entries}));
   return(evaluated.Select(t=>t.key).ToArray(),evaluated.Select(t=>t.o.ToWrpTransform(grid).M42).ToArray(),mask,roadHash,manifest,output.Count,pointPass.Length,roadPlants);
  }finally{ctx.DisposeHugeImages();}
 }
 await Run(job.State,job.Delta);
 Console.WriteLine("PASS guarded synthetic job; no export/runtime approval");return 0;
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
