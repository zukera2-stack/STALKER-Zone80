using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Zone80.Succession;
// Integer millimetres, synthetic axis-aligned geometry only. No production exporter.
public enum Land { Road, Courtyard, Parking, Sidewalk, Building }
public enum State { Operational, Abandoned, Unknown }
public enum Solid { None, VerifiedSolid, VerifiedOpening, Unknown }
public enum Origin { Observed, Procedural }
public enum Verdict { Allow, Deny, Review, NotSelected }
public sealed record Patch(string Id,Land Land,State State,Solid Solid,long X0,long Y0,long X1,long Y1,int DensityBps,int Years);
public sealed record Candidate(string Id,long X,long Y,Origin Origin);
public sealed record Decision(Candidate Candidate,Verdict Verdict,string Reason);
public sealed class Overlay {
 public const int Version=1;
 readonly Patch[] patches;
 public string Seed {get;}
 public Overlay(string seed,IEnumerable<Patch> items) {
  if(string.IsNullOrWhiteSpace(seed)||seed.Length>128)throw new ArgumentException("seed");
  Seed=seed; patches=items.OrderBy(p=>p.Id,StringComparer.Ordinal).ToArray();
  if(patches.Select(p=>p.Id).Distinct(StringComparer.Ordinal).Count()!=patches.Length)throw new ArgumentException("duplicate patch");
  foreach(var p in patches) if(string.IsNullOrWhiteSpace(p.Id)||p.X0>=p.X1||p.Y0>=p.Y1||p.DensityBps<0||p.DensityBps>10000||p.Years<0||!Enum.IsDefined(p.State)||!Enum.IsDefined(p.Land)||!Enum.IsDefined(p.Solid)||(p.Land!=Land.Building&&p.Solid!=Solid.None))throw new ArgumentException("invalid patch");
 }
 static bool Covers(Patch p,Candidate c)=>p.X0<=c.X&&c.X<p.X1&&p.Y0<=c.Y&&c.Y<p.Y1;
 static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
 // Hash only overlapping local state + seed; caller must provide the same halo on shared edges.
 public string Digest(long x0,long y0,long x1,long y1)=>Hash(JsonSerializer.SerializeToUtf8Bytes(new {Version,Seed,patches=patches.Where(p=>p.X0<x1&&p.X1>x0&&p.Y0<y1&&p.Y1>y0)}));
 public Decision Decide(Candidate c) {
  if(string.IsNullOrWhiteSpace(c.Id)||!Enum.IsDefined(c.Origin))throw new ArgumentException("candidate");
  var at=patches.Where(p=>Covers(p,c)).ToArray();
  Decision D(Verdict v,string reason)=>new(c,v,reason);
  if(at.Any(p=>p.Land==Land.Building&&p.Solid==Solid.VerifiedSolid))return D(Verdict.Deny,"verified solid");
  if(at.Any(p=>p.Land==Land.Road&&p.State==State.Operational))return D(Verdict.Deny,"protected passage");
  if(at.Length==0||at.Any(p=>p.State==State.Unknown||(p.Land==Land.Building&&p.Solid!=Solid.VerifiedOpening)))return D(Verdict.Review,"unknown state or geometry");
  if(at.Any(p=>p.State==State.Operational))return D(Verdict.Review,"operational non-road requires policy");
  if(c.Origin==Origin.Observed)return D(Verdict.Allow,"observed anchor retained");
  // Density is a scenario input, not inferred from age. Use most restrictive overlapping patch.
  var bytes=SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(new{Seed,c.Id,c.X,c.Y}));
  var sample=System.Buffers.Binary.BinaryPrimitives.ReadUInt32BigEndian(bytes);
  var density=at.Min(p=>p.DensityBps);
  return (ulong)sample*10000UL<(ulong)density*(1UL<<32)?D(Verdict.Allow,"procedural density selection"):D(Verdict.NotSelected,"procedural density selection");
 }
 public Decision[] Review(IEnumerable<Candidate> input,long x0,long y0,long x1,long y1) {
  var list=input.OrderBy(c=>c.Id,StringComparer.Ordinal).ToArray();
  if(list.Select(c=>c.Id).Distinct(StringComparer.Ordinal).Count()!=list.Length)throw new ArgumentException("duplicate ID");
  if(list.Select(c=>(c.X,c.Y)).Distinct().Count()!=list.Length)throw new ArgumentException("duplicate anchor requires review");
  if(x0>=x1||y0>=y1)throw new ArgumentException("bounds");
  return list.Where(c=>x0<=c.X&&c.X<x1&&y0<=c.Y&&c.Y<y1).Select(Decide).ToArray();
 }
}
