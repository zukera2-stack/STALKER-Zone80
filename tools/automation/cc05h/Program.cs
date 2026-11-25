using Zone80.Succession;
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
 var xml="<osm version=\"0.6\">"+Node(1,60,120)+Node(2,360,120)+"<way id=\"101\"><nd ref=\"1\"/><nd ref=\"2\"/><tag k=\"highway\" v=\"residential\"/></way>"+Node(3,180,120,"<tag k=\"natural\" v=\"tree\"/>")+"</osm>";
 var xmlHash=Hash(Encoding.UTF8.GetBytes(xml));
 var reviewed=new[]{typeof(ConditionEvaluator),typeof(TreesData),typeof(CategoryAreaData),typeof(CitiesData),typeof(OceanData),typeof(RoadsData),typeof(BuildingsData)};
 Patch P(string id,Land l,State s,Solid solid,long x0,long y0,long x1,long y1,int density=10000,int years=40)=>new(id,l,s,solid,x0,y0,x1,y1,density,years);
 var road=P("road",Land.Road,State.Abandoned,Solid.None,60000,116500,360000,123500);
 var observed=new Candidate("osm:3",180000,120000,Origin.Observed);
 var yard=P("yard",Land.Courtyard,State.Abandoned,Solid.None,0,200000,480000,400000);
 var parking=P("parking",Land.Parking,State.Abandoned,Solid.None,0,0,60000,60000);
 var sidewalk=P("walk",Land.Sidewalk,State.Abandoned,Solid.None,0,125000,480000,135000);
 var solid=P("solid",Land.Building,State.Abandoned,Solid.VerifiedSolid,100000,210000,150000,250000);
 var ruin=P("ruin",Land.Building,State.Abandoned,Solid.VerifiedOpening,200000,210000,250000,250000);
 var unknown=ruin with{Id="unknown",X0=300000,X1=350000,Solid=Solid.Unknown};
 var patches=new[]{road,yard,parking,sidewalk,solid,ruin,unknown};
 Overlay O(IEnumerable<Patch> ps)=>new("synthetic-v1",ps);
 var overlay=O(patches);
 var procedural=new[]{new Candidate("yard:1",160000,220000,Origin.Procedural),new Candidate("parking:1",30000,30000,Origin.Procedural),new Candidate("walk:1",160000,130000,Origin.Procedural),new Candidate("solid:1",120000,220000,Origin.Procedural),new Candidate("ruin:1",220000,220000,Origin.Procedural),new Candidate("unknown:1",320000,220000,Origin.Procedural),new Candidate("seam:1",240000,300000,Origin.Procedural)};
 var allPoints=procedural.Append(observed).ToArray();
 Check(overlay.Decide(observed).Verdict==Verdict.Allow,"abandoned road");
 Check(O(new[]{road with{State=State.Operational}}).Decide(observed).Verdict==Verdict.Deny,"operational road");
 Check(O(new[]{road with{State=State.Unknown}}).Decide(observed).Verdict==Verdict.Review,"unknown road");
 Check(O(new[]{road with{DensityBps=0}}).Decide(observed).Verdict==Verdict.Allow,"observed unaffected by density");
 var decisions=overlay.Review(allPoints,0,0,480000,480000);
 Check(decisions.Count(d=>d.Verdict==Verdict.Allow)==6&&decisions.Count(d=>d.Verdict==Verdict.Deny)==1&&decisions.Count(d=>d.Verdict==Verdict.Review)==1,"policy matrix");
 Check(decisions.SequenceEqual(O(patches.Reverse()).Review(allPoints.Reverse(),0,0,480000,480000)),"order repeat");
 Check(O(new[]{yard with{DensityBps=0}}).Decide(procedural[0]).Verdict==Verdict.NotSelected,"zero density");
 var half=O(new[]{yard with{DensityBps=5000}});var samples=Enumerable.Range(0,100).Select(i=>new Candidate("sample:"+i,160000+i,220000,Origin.Procedural)).ToArray();
 var count= samples.Count(c=>half.Decide(c).Verdict==Verdict.Allow);Check(count>0&&count<100,"partial density");
 Check(samples.Select(half.Decide).SequenceEqual(samples.Select(O(new[]{yard with{DensityBps=5000}}).Decide)),"seed repeat");
 var left=overlay.Review(allPoints,0,0,240000,480000);var right=overlay.Review(allPoints,240000,0,480000,480000);
 Check(left.Concat(right).OrderBy(d=>d.Candidate.Id,StringComparer.Ordinal).SequenceEqual(decisions),"seam ownership");
 var changed=O(patches.Select(p=>p.Id=="parking"?p with{DensityBps=0}:p));Check(changed.Digest(0,0,240000,480000)!=overlay.Digest(0,0,240000,480000)&&changed.Digest(240000,0,480000,480000)==overlay.Digest(240000,0,480000,480000),"local invalidation");
 void Refuse(Action a){try{a();}catch(ArgumentException){return;}throw new Exception("expected rejection");}
 Refuse(()=>overlay.Review(allPoints.Append(observed),0,0,480000,480000));Refuse(()=>overlay.Review(allPoints.Append(observed with{Id="duplicate"}),0,0,480000,480000));Refuse(()=>O(new[]{road with{DensityBps=10001}}));
 Console.WriteLine($"POLICY PASS allow=6 deny=1 review=1 partial_density={count}/100; seam, local invalidation, duplicates, invalid density, repeat PASS");
 async Task<string[]> Run(State state,bool stock=false,int delta=0){
  var rows=Enumerable.Range(0,16).Select(y=>string.Join(" ",Enumerable.Range(0,16).Select(x=>100+x+2*(15-y)+delta)));
  var asc=Encoding.ASCII.GetBytes("ncols 16\nnrows 16\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n"+string.Join("\n",rows)+"\n");
  var prj=Encoding.ASCII.GetBytes("synthetic fixture only");
  var input=NodeInput.Parse(asc,prj,new NodeContract(16,30,1000,2000,"EPSG:32636","EGM2008","m",Hash(asc),Hash(prj),"synthetic fixture only"));var grid=input.CopyGrid();
  var ctx=new BuildContext(new GuardedCatalog(new BuildersCatalog(assets,DefaultSourceLocations.Instance),reviewed),new NoProgress(),area,OsmDataSource.CreateFromInlineXml(xml),map,new MemoryHugeImageStorage());
  try{
   ctx.SetData(new ElevationData(grid));
   var roads=await ctx.GetDataAsync<RoadsData>(); Check(roads.Roads.Count==1,"native road");
   var original=new TerrainPoint(180,120); Check(roads.Roads[0].Polygons.Min(p=>p.Distance(original))==0,"native point inside road");
   if(!stock){
    // Explicit synthetic candidate adapter: inject only policy-selected anchors BEFORE requesting TreesData. Native TreesGenerator remains unchanged.
    var policy=O(patches.Select(p=>p.Id=="road"?p with{State=state}:p));
    var accepted=policy.Review(allPoints,0,0,480000,480000).Where(d=>d.Verdict==Verdict.Allow).Select(d=>new TerrainPoint(d.Candidate.X/1000f,d.Candidate.Y/1000f)).ToList();
    ctx.SetData(new TreesData(accepted));
   }
   var anchors=(await ctx.GetDataAsync<TreesData>()).Points.ToArray();
   var objects=(await generator.Generate(map,ctx,new NoProgress())).ToArray();
   var hasAnchor=anchors.Any(p=>Vector2.Distance(p.Vector,original.Vector)<0.001f);
   var onRoad=objects.Count(o=>roads.Roads[0].Polygons.Min(p=>p.Distance(o.Point))==0);
   Check(anchors.Length==objects.Length,"single composition record per anchor in pinned v03");
   var maxOffset=anchors.Zip(objects,(p,o)=>Vector2.Distance(p.Vector,o.Point.Vector)).Max();
   Check(maxOffset<3,"composition offset exceeds synthetic review bound");
   if(stock){Check(objects.Length==1&&!hasAnchor,"stock should displace road anchor");Console.WriteLine(FormattableString.Invariant($"STOCK anchor_shift_m={Vector2.Distance(anchors[0].Vector,original.Vector):F4}"));}
   else{Check(objects.Length==(state==State.Abandoned?6:5),"native count");Check(hasAnchor==(state==State.Abandoned),"native road anchor policy");Check(onRoad==(state==State.Abandoned?1:0),"native final road occupancy");}
   Console.WriteLine(FormattableString.Invariant($"COMPOSITION max_offset_m={maxOffset:F4} final_on_road={onRoad}"));
   Check(objects.All(o=>o.IsValid&&o.ElevationMode==ElevationMode.Relative&&treePaths.Contains(o.Model.Path)&&ReferenceEquals(o.Model,resolver.ResolveByPath(o.Model.Path))),"native model");
   Check(NodeInput.GridHash(grid)==input.Fingerprint,"grid mutation");
   var records=objects.Select(o=>o.ToTerrainBuilderCSV()).OrderBy(s=>s,StringComparer.Ordinal).ToArray();
   Console.WriteLine($"NATIVE state={state} stock={stock} count={records.Length} exact_road_anchor={hasAnchor} records_sha={Hash(Encoding.UTF8.GetBytes(string.Join("\n",records)))}");return records;
  }finally{ctx.DisposeHugeImages();}
 }
 await Run(State.Abandoned,true);var a=await Run(State.Abandoned);var b=await Run(State.Abandoned);Check(a.SequenceEqual(b),"native repeat");await Run(State.Operational);await Run(State.Unknown);
 Check(Hash(Encoding.UTF8.GetBytes(xml))==xmlHash&&Hash(File.ReadAllBytes(args[0]))==Hash(config)&&Hash(File.ReadAllBytes(args[1]))==Hash(cache),"source mutation");
 Console.WriteLine("PASS synthetic policy-aware native TreesGenerator; no production geometry or output");return 0;
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
