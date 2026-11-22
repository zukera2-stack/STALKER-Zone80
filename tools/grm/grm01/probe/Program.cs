using System.Numerics;
using System.Xml.Linq;
using GameRealisticMap.Arma3.TerrainBuilder;
using GameRealisticMap.Arma3.TerrainBuilder.TmlFiles;
using GameRealisticMap.Geometries;

if (args.Length != 1 || TerrainBuilderObject.XShift != 200000)
    throw new InvalidOperationException("Expected a fixture run directory and the pinned TB contract");

var model = new ModelInfo("FixtureMarker", @"fixture\marker.p3d", Vector3.Zero);
Check("W/absolute_fixture.txt", ElevationMode.Absolute, (32, 48, 105.75f));
Check("W/relative_fixture.txt", ElevationMode.Relative);
Check("E/absolute_fixture.txt", ElevationMode.Absolute, (256, 256, 98.25f));
Check("E/relative_fixture.txt", ElevationMode.Relative, (224, 72, -1.25f), (0, 80, 2.5f));
Check("world/absolute_fixture.txt", ElevationMode.Absolute, (32, 48, 105.75f), (512, 256, 98.25f));
Check("world/relative_fixture.txt", ElevationMode.Relative, (480, 72, -1.25f), (256, 80, 2.5f));

var library = Path.Combine(args[0], "probe-templates");
if (Directory.Exists(library))
    throw new IOException("Expected a fresh probe output directory");
new TmlGenerator().WriteLibrariesTo(new[] { model }, library);
var root = XDocument.Load(Path.Combine(library, "fixture.tml")).Root;
var template = root?.Elements("Template").Single();
if (root?.Name != "Library" || (string)template?.Element("Name") != model.Name ||
    (string)template?.Element("File") != model.Path)
    throw new InvalidOperationException("Unexpected GRM TML identity or model path");

Console.WriteLine("PASS: upstream CSV parity for all 6 files and synthetic TML identity");

void Check(string path, ElevationMode mode, params (float X, float Y, float Z)[] points)
{
    var expected = points.Select(p => new TerrainBuilderObject(
        model, new TerrainPoint(p.X, p.Y), p.Z, mode, 35, -7, 12, 1.25f).ToTerrainBuilderCSV());
    if (!File.ReadAllLines(Path.Combine(args[0], path)).SequenceEqual(expected))
        throw new InvalidOperationException($"CSV differs from upstream serializer: {path}");
}
