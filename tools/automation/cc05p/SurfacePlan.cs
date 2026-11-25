using GameRealisticMap;
using GameRealisticMap.Arma3;
using GameRealisticMap.Arma3.Assets;
using GameRealisticMap.Arma3.GameEngine;
using GameRealisticMap.Geometries;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Drawing.Processing;
using SixLabors.ImageSharp.Processing;
// Review-only explicit geometry plan; no elevation context or filesystem output.
sealed record SurfaceInput(string Evidence,List<TerrainPolygon> Polygons){
 public static SurfaceInput Geometry(IEnumerable<TerrainPolygon> p)=>new("synthetic_geometry",p.ToList());
 public static SurfaceInput Absent()=>new("known_absent_in_fixture",new());
}
static class SurfacePlan {
 // Observed draw precedence, not a copy of the internal renderer implementation.
 static readonly (string slot,TerrainMaterialUsage usage,bool edge)[] Order={
 ("urban",TerrainMaterialUsage.DefaultUrban,false),("industrial",TerrainMaterialUsage.DefaultIndustrial,false),("ocean",TerrainMaterialUsage.OceanGround,false),("coast",TerrainMaterialUsage.Coastline,true),("orchard",TerrainMaterialUsage.Grass,false),("vineyard",TerrainMaterialUsage.Grass,false),("forest",TerrainMaterialUsage.ForestGround,true),("meadow",TerrainMaterialUsage.Meadow,false),("farm",TerrainMaterialUsage.FarmLand,false),("ice",TerrainMaterialUsage.IceSurface,false),("sand",TerrainMaterialUsage.Sand,false),("grass",TerrainMaterialUsage.Grass,false),("river",TerrainMaterialUsage.RiverGround,false),("lake",TerrainMaterialUsage.LakeGround,false),("scree",TerrainMaterialUsage.ScreeSurface,false),("rock",TerrainMaterialUsage.RockGround,false),("asphalt",TerrainMaterialUsage.Asphalt,false)};
 public static Rgba32 Semantic(string name){int i=Array.FindIndex(Order,x=>x.slot==name);if(i<0&&name!="default")throw new InvalidDataException(name);return new Rgba32((byte)(i+2),0,0,255);}
 public static Dictionary<Rgba32,Rgba32> SemanticPalette(TerrainMaterialLibrary lib)=>Order.Select(x=>(Semantic(x.slot),new Color(lib.GetMaterialByUsage(x.usage).Id).ToPixel<Rgba32>())).Append((Semantic("default"),new Color(lib.GetMaterialByUsage(TerrainMaterialUsage.Default).Id).ToPixel<Rgba32>())).ToDictionary(x=>x.Item1,x=>x.Item2);
 public static void Validate(Dictionary<string,SurfaceInput> input){
 if(!input.Keys.ToHashSet(StringComparer.Ordinal).SetEquals(Order.Select(s=>s.slot)))throw new InvalidDataException("surface slots incomplete or unknown");
 foreach(var p in input.Values){if(p.Evidence=="known_absent_in_fixture"&&p.Polygons.Count==0)continue;if(p.Evidence!="synthetic_geometry"||p.Polygons.Count==0||p.Polygons.Any(x=>!double.IsFinite(x.Area)||x.Area<=0))throw new InvalidDataException("surface evidence invalid or unknown");}
 }
 public static (Image<Rgba32> material,Image<Rgba32> semantic) Render(IArma3MapConfig map,TerrainMaterialLibrary lib,Dictionary<string,SurfaceInput> input){
 Validate(input);var sz=map.GetIdMapSize();if(sz.Width!=480||sz.Height!=480)throw new InvalidDataException("synthetic fixture size only");
 var actual=new Image<Rgba32>(sz.Width,sz.Height,new Color(lib.GetMaterialByUsage(TerrainMaterialUsage.Default).Id).ToPixel<Rgba32>());var semantic=new Image<Rgba32>(sz.Width,sz.Height,Semantic("default"));
 var opts=new DrawingOptions();opts.GraphicsOptions.Antialias=false;
 try{
 foreach(var (slot,usage,edge) in Order){var mat=lib.GetMaterialByUsage(usage);var col=new Color(mat.Id);var sem=new Color(Semantic(slot));
 var polys=input[slot].Polygons;
 void Draw(Image<Rgba32> img,IEnumerable<TerrainPolygon> p,Brush brush)=>img.Mutate(d=>{foreach(var polygon in p)PolygonDrawHelper.DrawPolygon(d,polygon,brush,opts,pts=>map.TerrainToIdMapPixel(pts));});
 Draw(actual,polys,new SolidBrush(col));Draw(semantic,polys,new SolidBrush(sem));
 if(edge){ // Explicit review candidate: seeded 64x64 edge stipple; not a byte-equivalence claim to internal IdMapRender.
 var rng=new Random(mat.Id.R*65536+mat.Id.G*256+mat.Id.B);var pattern=new bool[64,64];for(int x=0;x<64;x++)for(int y=0;y<64;y++)pattern[x,y]=rng.NextDouble()>=0.5;
 var crown=polys.SelectMany(p=>p.OuterCrown(2.5f)).ToList();Draw(actual,crown,new PatternBrush(col,Color.Transparent,pattern));Draw(semantic,crown,new PatternBrush(sem,Color.Transparent,pattern));
 }
 }
 return(actual,semantic);
 }catch{actual.Dispose();semantic.Dispose();throw;}
 }
}
