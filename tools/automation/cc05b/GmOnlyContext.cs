using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Buffers.Binary;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using GameRealisticMap;
using GameRealisticMap.ElevationModel;
using GameRealisticMap.Osm;
using Pmad.HugeImages.Storage;
using Pmad.ProgressTracking;

namespace Zone80.GmBridge;

// Trusted, independently reviewed metadata: hashes are identity, not authenticity.
public sealed record NodeContract(int Size, decimal Step, decimal East, decimal North,
    string Crs, string Datum, string Units, string AscSha256, string PrjSha256,
    string Evidence, string GridSemantics = "pixel_center_on_grm_node");

public sealed class NodeInput
{
    private readonly float[,] values;
    public NodeContract Contract { get; }
    public string Fingerprint { get; }
    private NodeInput(NodeContract c, float[,] v)
    { Contract = c; values = v; Fingerprint = Hash(v); }
    private static void Need(bool yes, string reason)
    { if (!yes) throw new InvalidDataException(reason); }
    private static string Hex(byte[] b) => Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
    private static decimal Num(string s)
    {
        Need(s.Length <= 40 && Regex.IsMatch(s, @"\A[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,3})?\z") && decimal.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out _), "number");
        var n=decimal.Parse(s, NumberStyles.Float, CultureInfo.InvariantCulture);
        Need(Math.Abs(n)<=100000000m && (n==0 || Math.Abs(n)>=0.000000000001m), "numeric range");
        // Reject nonzero mantissas that underflowed Decimal to zero.
        Need(n!=0 || !s.Split('e','E')[0].Any(ch=>ch>='1' && ch<='9'), "underflow");
        return n;
    }
    private static string[] Fields(string? line) => (line ?? "").Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
    public static NodeInput Parse(byte[] asc, byte[] prj, NodeContract c)
    {
        Need(c.Size >= 2 && c.Size <= 64 && c.Step > 0 && c.Step <= 100 && c.Step==decimal.Truncate(c.Step), "pilot bounds");
        Need(c.Crs == "EPSG:32636" && c.Datum == "EGM2008" && c.Units == "m" && !string.IsNullOrWhiteSpace(c.Evidence) && c.GridSemantics=="pixel_center_on_grm_node", "metadata");
        Need(asc.Length <= 1048576 && prj.Length <= 65536 && Hex(asc) == c.AscSha256 && Hex(prj) == c.PrjSha256, "input hash/size");
        Need(asc.All(b => b < 128), "non-ASCII ASC");
        using var r = new StringReader(Encoding.ASCII.GetString(asc));
        var h = new Dictionary<string, decimal>(StringComparer.OrdinalIgnoreCase);
        for (int i=0; i<6; i++)
        { var f=Fields(r.ReadLine()); Need(f.Length==2,"header"); Need(h.TryAdd(f[0],Num(f[1])),"duplicate header"); }
        Need(new[]{"ncols","nrows","xllcorner","yllcorner","cellsize","nodata_value"}.All(h.ContainsKey),"header keys");
        Need(h["ncols"]==c.Size && h["nrows"]==c.Size && h["cellsize"]==c.Step && h["nodata_value"]==-9999,"grid");
        Need(h["xllcorner"]+c.Step/2==c.East && h["yllcorner"]+c.Step/2==c.North,"center/node mismatch");
        var data=new float[c.Size,c.Size];
        for(int northRow=0;northRow<c.Size;northRow++)
        {
            var f=Fields(r.ReadLine()); Need(f.Length==c.Size,"row length");
            for(int x=0;x<c.Size;x++)
            { var v=Num(f[x]); Need(v!=-9999 && v>=-12000 && v<=12000,"NoData/range"); data[c.Size-1-northRow,x]=(float)v; }
        }
        Need(r.ReadLine()==null,"extra row");
        return new NodeInput(c,data);
    }
    internal ElevationGrid CopyGrid()
    {
        var grid=new ElevationGrid(Contract.Size,(float)Contract.Step);
        for(int y=0;y<Contract.Size;y++) for(int x=0;x<Contract.Size;x++) grid[x,y]=values[y,x];
        return grid;
    }
    internal static string GridHash(ElevationGrid grid)
    {
        var data=new float[grid.Size,grid.Size];
        for(int y=0;y<grid.Size;y++) for(int x=0;x<grid.Size;x++) data[y,x]=grid[x,y];
        return Hash(data);
    }
    private static string Hash(float[,] data)
    {
        byte[] bytes=new byte[checked(data.Length*4)]; int i=0;
        for(int y=0;y<data.GetLength(0);y++) for(int x=0;x<data.GetLength(1);x++,i+=4)
            BinaryPrimitives.WriteInt32LittleEndian(bytes.AsSpan(i,4),BitConverter.SingleToInt32Bits(data[y,x]));
        return Hex(bytes);
    }
}

// No default fallback. Only exact types in a reviewed, code-owned allowlist.
// In this prototype the actual native layer allowlist is empty.
public sealed class GuardedCatalog : IBuidersCatalog
{
    private readonly IBuidersCatalog inner;
    private readonly HashSet<Type> allowed;
    public GuardedCatalog(IBuidersCatalog inner, IEnumerable<Type> reviewed)
    {
        this.inner=inner; allowed=new HashSet<Type>(reviewed);
        foreach(var t in allowed)
            if(t.Namespace?.StartsWith("GameRealisticMap.ElevationModel",StringComparison.Ordinal)==true ||
               t.Namespace?.StartsWith("GameRealisticMap.Satellite",StringComparison.Ordinal)==true ||
               t.Namespace?.StartsWith("GameRealisticMap.Nature.Weather",StringComparison.Ordinal)==true)
                throw new InvalidOperationException("Forbidden builder type: "+t.FullName);
    }
    public IDataBuilder<T> Get<T>() where T:class
    {
        if(!allowed.Contains(typeof(T))) throw new InvalidOperationException("Unreviewed builder: "+typeof(T).FullName);
        return inner.Get<T>();
    }
    public void Register<T>(IDataBuilder<T> builder) where T:class => throw new NotSupportedException("sealed registry");
    public IEnumerable<TResult> VisitAll<TResult>(IDataBuilderVisitor<TResult> visitor) => throw new NotSupportedException("bulk builders disabled");
    public IEnumerable<T> GetOfType<T>(IContext ctx, Func<Type,bool>? filter=null) where T:class => throw new NotSupportedException("bulk builders disabled");
    public IEnumerable<object> GetAll(IContext ctx) => throw new NotSupportedException("bulk builders disabled");
}

// Bounded source-level integration seam; no CLI/native generation entrypoint.
// The supplied area must be independently checked in GRM against the exact UTM control points.
public sealed class GmSession : IDisposable
{
    private readonly BuildContext context;
    private readonly NodeInput input;
    private readonly ElevationGrid grid;
    private bool used;
    private GmSession(NodeInput input, BuildContext context, ElevationGrid grid)
    { this.input=input; this.context=context; this.grid=grid; }
    public static GmSession CreateSynthetic(NodeInput input, IBuidersCatalog catalog, IProgressScope progress,
        ITerrainArea area, IOsmDataSource osm, IMapProcessingOptions options, IHugeImageStorage storage)
    {
        if(input.Contract.Evidence!="synthetic fixture only") throw new InvalidOperationException("real context disabled");
        if(area.GridSize!=input.Contract.Size || area.GridCellSize!=(float)input.Contract.Step)
            throw new InvalidOperationException("GRM area grid mismatch");
        // Intentionally empty until real layer-specific graph has been reviewed.
        var guarded=new GuardedCatalog(catalog,Array.Empty<Type>());
        var context=new BuildContext(guarded,progress,area,osm,options,storage);
        var grid=input.CopyGrid();
        context.SetData(new ElevationData(grid)); // before any worker tasks start
        return new GmSession(input,context,grid);
    }
    // Only prebuilt synthetic support data. Never seed RawElevationData or fake lake metadata.
    public void SeedSynthetic<T>(T value) where T:class
    {
        if(used || !new[]{"GameRealisticMap.ManMade.CategoryAreaData","GameRealisticMap.ManMade.Places.CitiesData","GameRealisticMap.Nature.Ocean.OceanData","GameRealisticMap.ManMade.Roads.RoadsData"}.Contains(typeof(T).FullName))
            throw new InvalidOperationException("unapproved synthetic seed");
        context.SetData(value);
    }
    public async Task<T> ProbeAsync<T>(Func<IContext,Task<T>> probe)
    {
        if(used) throw new InvalidOperationException("session already used");
        used=true;
        try { return await probe(context); }
        finally
        {
            if(NodeInput.GridHash(grid)!=input.Fingerprint) throw new InvalidOperationException("GM grid mutation detected; discard result");
        }
    }
    public void Dispose()=>context.DisposeHugeImages();
}
