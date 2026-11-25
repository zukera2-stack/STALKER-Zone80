using System.Diagnostics.CodeAnalysis;
using System.Security.Cryptography;
using System.Text.Json;
using GameRealisticMap.Arma3;
using GameRealisticMap.Arma3.Assets;
using GameRealisticMap.Arma3.TerrainBuilder;
using GameRealisticMap.Geometries;
using GeoAPI.Geometries;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;

// Read-only review probe, pinned editor configuration. Never calls a generator.
static void Require(bool b,string message) {if(!b) throw new InvalidDataException(message);}
static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
if(args.Length!=2) throw new ArgumentException("v03.grma3a and pinned pilot.grma3m paths required");
var source=File.ReadAllBytes(args[0]);
Require(Hash(source)=="418a6b1db5493c8b9f89f288024a769522f568483a5e614383d934506e7a941e","v03 hash");
var map=File.ReadAllBytes(args[1]);
Require(Hash(map)=="ba1fec76209e3af86c44c6132228c0599df43a3d775ad5f3ebce1b52f63d14e4","pilot config hash");
using var raw=JsonDocument.Parse(source);
var reject=new RejectModels();
try { _=JsonSerializer.Deserialize<Arma3Assets>(source,Arma3Assets.CreateJsonSerializerOptions(reject,false)); throw new InvalidDataException("strict parse unexpectedly resolved models"); }
catch(ApplicationException e) when(e.Message.StartsWith("Model '") && e.Message.Contains("was not found")) {Console.WriteLine("STRICT_MODEL_RESOLUTION BLOCKED as expected");}
Require(reject.Paths.Count==1,"strict first missing reference");
var review=new RejectModels();
var assets=JsonSerializer.Deserialize<Arma3Assets>(source,Arma3Assets.CreateJsonSerializerOptions(review,true))??throw new Exception("parse null");
var definitions=raw.RootElement.GetProperty("Materials").GetProperty("Definitions");
Require(assets.Materials.Definitions.Count==11 && definitions.GetArrayLength()==11,"material count");
var usages=new HashSet<TerrainMaterialUsage>();var colors=new HashSet<Rgb24>();int surfaceCount=0;
for(int i=0;i<11;i++) {
 var d=assets.Materials.Definitions[i];var r=definitions[i];var m=r.GetProperty("Material");
 Require(d.Material.Id==Color.Parse(m.GetProperty("Id").GetString()!).ToPixel<Rgb24>() && colors.Add(d.Material.Id),"color");
 Require(d.Material.ColorTexture==m.GetProperty("ColorTexture").GetString() && d.Material.NormalTexture==m.GetProperty("NormalTexture").GetString(),"textures");
 Require(d.Usages.Select(u=>u.ToString()).SequenceEqual(r.GetProperty("Usages").EnumerateArray().Select(u=>u.GetString())),"usages");
 foreach(var u in d.Usages) Require(usages.Add(u)&&ReferenceEquals(assets.Materials.GetMaterialByUsage(u),d.Material),"usage index");
 var has=r.TryGetProperty("Surface",out var surf)&&surf.ValueKind!=JsonValueKind.Null;
 Require(has==(d.Surface!=null),"surface lost in parser");
 if(has){Require(d.Surface!.Name==surf.GetProperty("Name").GetString(),"surface name");surfaceCount++;}
}
Require(usages.SetEquals(Enum.GetValues<TerrainMaterialUsage>()),"missing usage");
Require(assets.Roads.Count==9 && assets.Roads.Select(r=>r.Id).Distinct().Count()==9,"roads");
Require(assets.Buildings.Values.All(x=>x.Count==0) && assets.Ponds.Values.All(x=>x==null) && assets.Sidewalks.Count==0,"disabled groups");
Require(assets.BaseWorldName=="arm_world_centraleurope" && assets.BaseDependency=="arm_centraleurope" && assets.Dependencies.Count==0,"base still external");
Console.WriteLine($"EDITOR_REVIEW_PARSE PASS material_defs={colors.Count} usages={usages.Count} surfaces={surfaceCount} roads={assets.Roads.Count} unresolved_model_paths={review.Paths.Count} runtime_approved=0");
Console.WriteLine("PRODUCTION BLOCKED: missing verified model metadata, external base, ice and mud review");
var mapJson=JsonSerializer.Deserialize<Arma3MapConfigJson>(map)??throw new Exception("map parse");
Require(mapJson.SouthWest=="51.397007839, 30.043987574" && mapJson.Center==null && mapJson.GridSize==64 && mapJson.GridCellSize==30 && mapJson.AssetConfigFile=="builtin:CentralEurope.grma3a" && mapJson.TargetModDirectory==null,"pilot candidate drift");
// In-memory review only; do not invoke default Documents output resolution or builtin assets.
mapJson.TargetModDirectory="REVIEW_ONLY_UNUSED";mapJson.AssetConfigFile="REVIEW_ONLY_UNUSED";
var cfg=mapJson.ToArma3MapConfig();var area=cfg.TerrainArea;
Require(area.GridSize==64&&area.GridCellSize==30&&area.SizeInMeters==1920,"pilot grid");
var corners=new[]{(0f,0f,30.043987574,51.397007839),(0f,1920f,30.042874782,51.414249232),(1920f,0f,30.071549833,51.397700371),(1920f,1920f,30.070447379,51.414942189)};
double max=0,absoluteMax=0;
foreach(var (x,y,lon,lat) in corners){var p=area.LatLngToTerrainPoint(new Coordinate(lon,lat));var err=Math.Sqrt(Math.Pow(p.X-x,2)+Math.Pow(p.Y-y,2));max=Math.Max(max,err); var ll=area.TerrainPointToLatLng(new TerrainPoint(x,y));var u=new CoordinateSharp.Coordinate(ll.Y,ll.X).UTM;Require(u.LongZone==36,"zone");var absolute=Math.Sqrt(Math.Pow(u.Easting-(294373.084+x),2)+Math.Pow(u.Northing-(5698122.108+y),2));absoluteMax=Math.Max(absoluteMax,absolute);Console.WriteLine(FormattableString.Invariant($"corner {x},{y} local_error_m={err:F6} absolute_utm_error_m={absolute:F6}"));}
Console.WriteLine(FormattableString.Invariant($"COORDINATE_REVIEW max_local_m={max:F6} max_absolute_utm_m={absoluteMax:F6} threshold_m=0.2"));
Require(max<=0.2&&absoluteMax<=0.2,"pilot coordinate tolerance (review threshold)");
Require(Hash(File.ReadAllBytes(args[0]))==Hash(source)&&Hash(File.ReadAllBytes(args[1]))==Hash(map),"input mutated");
Console.WriteLine("PASS REVIEW ONLY; no generation or native placement");
sealed class RejectModels:IModelInfoLibrary {
 public HashSet<string> Paths {get;}=new(StringComparer.OrdinalIgnoreCase);
 public bool TryResolveByPath(string path,[MaybeNullWhen(false)] out ModelInfo model){Paths.Add(path);model=null;return false;}
 public bool TryResolveByName(string name,[MaybeNullWhen(false)] out ModelInfo model){model=null;return false;}
 public ModelInfo ResolveByName(string name)=>throw new InvalidOperationException("review-only");
 public ModelInfo ResolveByPath(string path)=>throw new InvalidOperationException("review-only");
 public bool TryRegister(string name,string path)=>throw new InvalidOperationException("review-only");
 public bool? IsSlopeLandContact(string path)=>null;
 public string? TryGetNoLandContact(string path)=>null;
}
