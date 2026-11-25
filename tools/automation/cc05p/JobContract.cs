using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

// Closed fixture-only contract. No arbitrary paths, commands, source coordinates or layer activation.
sealed record JobContract(string State, int Delta, string Id)
{
    public const string ConfigHash = "418a6b1db5493c8b9f89f288024a769522f568483a5e614383d934506e7a941e";
    public const string CacheHash = "1177ec6d4618f198bd40f79880d3434ecbd7e0b8414881e23159c3e2a4cd9e94";
    public const string OsmHash = "d20dbe01972c981946bf17254f94a8180cbbd7c867e9741d88a91301fa0a222c";
    public const string Fixture = "cc05o-inline-480m-v1";
    public static string Hash(string s) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(s))).ToLowerInvariant();
    static void Need(bool ok, string why) { if (!ok) throw new InvalidDataException("job: " + why); }
    public static JobContract Parse(byte[] bytes)
    {
        Need(bytes.Length is > 0 and <= 8192, "size");
        using var doc = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 4 });
        var root = doc.RootElement;
        Need(root.ValueKind == JsonValueKind.Object, "object required");
        var fields = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        foreach (var p in root.EnumerateObject()) Need(fields.TryAdd(p.Name,p.Value), "duplicate key");
        string[] expected = ["schema_version", "scope", "fixture", "road_state", "height_delta_m", "config_sha256", "cache_sha256", "osm_sha256", "export"];
        Need(fields.Keys.ToHashSet(StringComparer.Ordinal).SetEquals(expected), "exact fields required");
        string Str(string n) { Need(fields[n].ValueKind == JsonValueKind.String, n + " type"); return fields[n].GetString()!; }
        int Int(string n) { Need(fields[n].ValueKind == JsonValueKind.Number && fields[n].TryGetInt32(out _), n + " integer"); return fields[n].GetInt32(); }
        Need(Int("schema_version") == 1, "schema version");
        Need(Str("scope") == "synthetic_review_only", "scope");
        Need(Str("fixture") == Fixture, "fixture");
        string state = Str("road_state"); Need(state is "abandoned" or "operational" or "unknown", "road state");
        int delta = Int("height_delta_m"); Need(delta is 0 or 100, "height delta");
        Need(Str("config_sha256") == ConfigHash && Str("cache_sha256") == CacheHash && Str("osm_sha256") == OsmHash, "input hashes");
        Need(fields["export"].ValueKind == JsonValueKind.False, "export prohibited");
        string canonical = $"cc05p-job-v1\nsynthetic_review_only\n{Fixture}\n{state}\n{delta.ToString(CultureInfo.InvariantCulture)}\n{ConfigHash}\n{CacheHash}\n{OsmHash}\nfalse";
        return new(state, delta, Hash(canonical));
    }
}
sealed record LayerDisposition(string Name, string Status, string Reason);
static class CatalogPolicy
{
    public static readonly LayerDisposition[] Entries = [
        new("OrientedObjectsGenerator","enabled_synthetic","explicit OSM objects"),
        new("BridgeGenerator","enabled_synthetic","reviewed native bridge placement"),
        new("FenceGenerator","enabled_synthetic","reviewed explicit barriers"),
        new("RailwayGenerator","enabled_synthetic","reviewed native rail placement"),
        new("ForestEdgeGenerator","enabled_synthetic","reviewed forest geometry"),
        new("ForestGenerator","enabled_synthetic","reviewed forest geometry"),
        new("ForestRadialGenerator","enabled_synthetic","reviewed bounded radial geometry"),
        new("ScrubGenerator","enabled_synthetic","reviewed bounded scrub geometry"),
        new("ScrubRadialGenerator","enabled_synthetic","reviewed bounded radial geometry"),
        new("TreesGenerator","enabled_synthetic","explicit observed anchors"),
        new("TreeRowsGenerator","enabled_synthetic","explicit tree rows only"),
        new("WatercourseGenerator","enabled_synthetic","reviewed bounded watercourse geometry"),
        new("SidewalksGenerator","disabled_verified_empty","v03 disables automatic sidewalks; invoke only to verify zero"),
        new("BuildingGenerator","disabled_zpb","historical buildings belong to ZPB; no generic substitution"),
        new("DefaultAgriculturalAreasGenerator","pending_review","generic fill not reviewed"),
        new("DefaultCommercialAreasGenerator","pending_review","generic fill not reviewed"),
        new("DefaultIndustrialAreasGenerator","pending_review","generic fill not reviewed"),
        new("DefaultMilitaryAreasGenerator","pending_review","generic fill not reviewed"),
        new("DefaultResidentialAreasGenerator","pending_review","generic fill not reviewed"),
        new("DefaultRetailAreasGenerator","pending_review","generic fill not reviewed"),
        new("DefaultAreasGenerator","pending_review","generic fill not reviewed"),
        new("LakeSurfaceGenerator","pending_review","water plane and pond models not approved"),
        new("OrchardGenerator","pending_review","actual agricultural geometry/state not reviewed"),
        new("RocksGenerator","pending_review","actual placement and slope review absent"),
        new("ScreeGenerator","pending_review","actual placement and slope review absent"),
        new("VineyardsGenerator","pending_review","regional and historical review absent"),
        new("WatercourseRadialGenerator","pending_review","stock elevation dependency refused")
    ];
    public static HashSet<string> Validate(IEnumerable<string> nativeNames)
    {
        var actual = nativeNames.ToArray();
        if (actual.Length != Entries.Length || actual.Distinct(StringComparer.Ordinal).Count()!=actual.Length || !actual.ToHashSet(StringComparer.Ordinal).SetEquals(Entries.Select(x=>x.Name)))
            throw new InvalidDataException("unreviewed native catalog");
        return Entries.Where(e=>e.Status is "enabled_synthetic" or "disabled_verified_empty").Select(e=>e.Name).ToHashSet(StringComparer.Ordinal);
    }
}
