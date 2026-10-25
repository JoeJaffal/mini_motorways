// Read-only component oracle. Loads installed assemblies in place; never bundles or edits them.
using System.Reflection;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text.Json;
if(args.Length!=1&&args.Length!=3)throw new ArgumentException("Pass the installed game's Managed directory, optionally followed by --rail and a numeric rail fixture JSON.");
string managed=Path.GetFullPath(args[0]);
AssemblyLoadContext.Default.Resolving+=(context,name)=>{string p=Path.Combine(managed,name.Name+".dll");return File.Exists(p)?context.LoadFromAssemblyPath(p):null;};
string appPath=Path.Combine(managed,"App.dll");
var assembly=AssemblyLoadContext.Default.LoadFromAssemblyPath(appPath);
if(args.Length==3)
{
 if(args[1]!="--rail")throw new ArgumentException("Expected --rail.");
 var unity=AssemblyLoadContext.Default.LoadFromAssemblyPath(Path.Combine(managed,"UnityEngine.CoreModule.dll"));
 var vector=unity.GetType("UnityEngine.Vector2Int",true);var railType=assembly.GetType("Motorways.RailType",true);
 var dictionaryType=typeof(Dictionary<,>).MakeGenericType(vector,railType);var dictionary=Activator.CreateInstance(dictionaryType);
 using var fixture=JsonDocument.Parse(File.ReadAllText(args[2]));
 foreach(var cell in fixture.RootElement.EnumerateArray())
 {
  var position=Activator.CreateInstance(vector,new object[]{cell.GetProperty("x").GetInt32(),cell.GetProperty("y").GetInt32()});
  var kind=Enum.Parse(railType,cell.TryGetProperty("origin",out var origin)&&origin.GetBoolean()?"TrainOrigin":"Normal");
  dictionaryType.GetMethod("Add").Invoke(dictionary,new[]{position,kind});
 }
 var networkType=assembly.GetType("Motorways.TrainNetworkDefinition",true);
 var network=networkType.GetMethod("CreateFromRailTileCoordinates").Invoke(null,new[]{dictionary});
 var lines=new List<object>();
 foreach(var line in (System.Collections.IEnumerable)networkType.GetProperty("TrainLines").GetValue(network))
 {
  var lineType=line.GetType();var cells=new List<object>();
  for(int i=0;i<(int)lineType.GetProperty("TileCount").GetValue(line);i++)
  {
   var position=lineType.GetMethod("GetRailTileCoordinates").Invoke(line,new object[]{i});
   cells.Add(new{x=(int)vector.GetProperty("x").GetValue(position),y=(int)vector.GetProperty("y").GetValue(position),origin=lineType.GetMethod("GetRailTileType").Invoke(line,new object[]{i}).ToString()=="TrainOrigin"});
  }
  lines.Add(new{loop=(bool)lineType.GetField("isLoop").GetValue(line),valid=(bool)lineType.GetField("isValid").GetValue(line),cells});
 }
 Console.WriteLine(JsonSerializer.Serialize(new{source="Invoked installed rail topology component; does not validate train movement",assemblySha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(appPath))).ToLowerInvariant(),lines},new JsonSerializerOptions{WriteIndented=true}));
 return;
}
var type=assembly.GetType("PseudorandomGenerator",true);
var result=new List<object>();
foreach(ulong seed in new ulong[]{0,1,42,2147483647,4294967295})
{
 object make(){var obj=Activator.CreateInstance(type);type.GetProperty("Seed").SetValue(obj,seed);return obj;}
 var obj=make();var ints=new List<int>();for(int i=0;i<12;i++)ints.Add((int)type.GetMethod("Int",Type.EmptyTypes).Invoke(obj,null));
 obj=make();var bounded=new List<int>();for(int i=0;i<12;i++)bounded.Add((int)type.GetMethod("Int",new[]{typeof(int)}).Invoke(obj,new object[]{17}));
 obj=make();var fractions=new List<long>();for(int i=0;i<12;i++){var fix=type.GetMethod("Fix64",Type.EmptyTypes).Invoke(obj,null);var f=fix.GetType().GetField("m_rawValue",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance);fractions.Add((long)f.GetValue(fix));}
 result.Add(new{seed,ints,bounded,fractionRaw=fractions});
}
Console.WriteLine(JsonSerializer.Serialize(new{source="Invoked installed assembly; no original assemblies bundled",assemblySha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(appPath))).ToLowerInvariant(),vectors=result},new JsonSerializerOptions{WriteIndented=true}));
