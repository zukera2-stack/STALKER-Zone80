using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Linq;
using System.Web.Script.Serialization;
using System.Windows.Automation;

internal static class UiaInventory
{
    private const string Target = @"WinSta0\Default";
    private const string ExpectedHash = "69470C7FB029C5D63F849FDDB197DCE715ED219F7AE08BEC132472FF333A7AC7";

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct Startup
    {
        public uint Size;
        public string Reserved, Desktop, Title;
        public uint X, Y, Width, Height, Columns, Rows, Fill, Flags;
        public ushort Show, ReservedBytes;
        public IntPtr ReservedData, Input, Output, Error;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct ProcessInfo
    {
        public IntPtr Process, Thread;
        public uint Pid, Tid;
    }

    [DllImport("kernel32.dll", ExactSpelling = true, CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CreateProcessW(string application, StringBuilder command, IntPtr processAttributes,
        IntPtr threadAttributes, bool inheritHandles, uint flags, IntPtr environment, string directory,
        ref Startup startup, out ProcessInfo info);
    [DllImport("kernel32.dll")] private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] private static extern uint GetCurrentThreadId();
    [DllImport("kernel32.dll")] private static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("user32.dll")] private static extern IntPtr GetProcessWindowStation();
    [DllImport("user32.dll")] private static extern IntPtr GetThreadDesktop(uint thread);
    [DllImport("user32.dll", SetLastError = true)] private static extern IntPtr OpenInputDesktop(uint flags, bool inherit, uint access);
    [DllImport("user32.dll", EntryPoint = "OpenDesktopW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr OpenDesktop(string name, uint flags, bool inherit, uint access);
    [DllImport("user32.dll")] private static extern bool CloseDesktop(IntPtr handle);
    [DllImport("user32.dll", EntryPoint = "GetUserObjectInformationW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ObjectName(IntPtr handle, int index, StringBuilder name, int size, out int required);
    private delegate bool WindowCallback(IntPtr window, IntPtr param);
    [DllImport("user32.dll", SetLastError = true)] private static extern bool EnumDesktopWindows(IntPtr desktop, WindowCallback callback, IntPtr param);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetWindowText(IntPtr window, StringBuilder text, int capacity);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetClassName(IntPtr window, StringBuilder text, int capacity);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);

    private static Win32Exception LastError(string api)
    {
        int error = Marshal.GetLastWin32Error();
        return new Win32Exception(error, api);
    }

    private static string Name(IntPtr handle)
    {
        var name = new StringBuilder(256);
        int required;
        if (!ObjectName(handle, 2, name, name.Capacity * 2, out required))
            throw LastError("GetUserObjectInformationW");
        return name.ToString();
    }

    [DllImport("kernel32.dll", SetLastError = true)] private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool GetExitCodeProcess(IntPtr handle, out uint code);

    private static ProcessInfo Launch(string exe, string args)
    {
        var startup = new Startup { Size = (uint)Marshal.SizeOf(typeof(Startup)), Desktop = Target };
        var cmd = new StringBuilder("\"" + exe + "\"" + args);
        ProcessInfo info;
        if (!CreateProcessW(exe, cmd, IntPtr.Zero, IntPtr.Zero, false, 0, IntPtr.Zero,
            Path.GetDirectoryName(exe), ref startup, out info))
            throw LastError("CreateProcessW");
        CloseHandle(info.Thread);
        return info;
    }

    private static string Desktop()
    {
        return Name(GetProcessWindowStation()) + @"\" + Name(GetThreadDesktop(GetCurrentThreadId()));
    }

    private static string ExpectedExe()
    {
        return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
            @"Steam\steamapps\common\Arma 3 Tools\TerrainBuilder\TerrainBuilder.exe");
    }

    private static string Hash(string path)
    {
        using (var sha = SHA256.Create())
        using (var file = File.OpenRead(path))
            return BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "");
    }

    private static bool Matches(string name, string path, long observed, long expected, string hash)
    {
        return name == "TerrainBuilder" && String.Equals(path, ExpectedExe(), StringComparison.OrdinalIgnoreCase)
            && observed == expected && hash == ExpectedHash;
    }

    private static bool IsTarget(string desktop) { return desktop == Target; }

    private static StreamWriter NewLog(string path)
    {
        return new StreamWriter(new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read)) { AutoFlush = true };
    }

    private static bool Owns(uint expected, uint actual, IntPtr hwnd)
    {
        return hwnd != IntPtr.Zero && expected == actual;
    }

    private static int WaitResult(uint wait)
    {
        return wait == 0 ? 0 : wait == 258 ? 5 : 2;
    }

    private static readonly JavaScriptSerializer Json = new JavaScriptSerializer();

    private static int SelfTest(string dir)
    {
        string sample = "quoted \"text\"\nnew line";
        if (Json.Deserialize<string>(Json.Serialize(sample)) != sample ||
            !Owns(7, 7, new IntPtr(1)) || Owns(7, 8, new IntPtr(1)) || Owns(7, 7, IntPtr.Zero) ||
            WaitResult(0) != 0 || WaitResult(258) != 5 || WaitResult(0xffffffff) != 2)
            return 2;
        if (!Matches("TerrainBuilder", ExpectedExe(), 1, 1, ExpectedHash) ||
            Matches("TerrainBuilder", ExpectedExe(), 2, 1, ExpectedHash)) return 2;
        Console.WriteLine("PASS: JSON round trip, owner/HWND isolation, identity, wait result");
        return 0;
    }

    [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr window);
    [DllImport("user32.dll")] private static extern bool IsWindowEnabled(IntPtr window);

    private static int Inspect(int pid, long ticks, IntPtr desktop)
    {
        Process found;
        try { found = Process.GetProcessById(pid); }
        catch (ArgumentException) { Console.WriteLine("ABSENT pid={0}", pid); return 3; }

        using (found)
        {
            if (found.ProcessName != "TerrainBuilder") throw new InvalidOperationException("Process name mismatch.");
            var image = found.MainModule.FileName;
            long started = found.StartTime.ToUniversalTime().Ticks;
            string hash = Hash(image);
            if (!Matches(found.ProcessName, image, started, ticks, hash))
                throw new InvalidOperationException("Process identity mismatch.");
            Console.WriteLine("verified pid={0}; utc={1:o}; session={2}; SHA256={3}; WS={4}; private={5}; responding={6}",
                pid, found.StartTime.ToUniversalTime(), found.SessionId, hash, found.WorkingSet64, found.PrivateMemorySize64, found.Responding);
            bool editor = false, dialog = false, uia = false;
            int budget = 500, errors = 0;
            var timer = Stopwatch.StartNew();
            bool enumerated = EnumDesktopWindows(desktop, delegate(IntPtr window, IntPtr ignored)
            {
                uint owner;
                GetWindowThreadProcessId(window, out owner);
                if (!Owns((uint)pid, owner, window)) return true;
                var title = new StringBuilder(512);
                var cls = new StringBuilder(256);
                GetWindowText(window, title, title.Capacity);
                GetClassName(window, cls, cls.Capacity);
                bool visible = IsWindowVisible(window), enabled = IsWindowEnabled(window), minimized = IsIconic(window);
                Console.WriteLine("HWND=0x{0:X}; class={1}; visible={2}; enabled={3}; minimized={4}; title={5}",
                    window.ToInt64(), cls, visible, enabled, minimized, title);
                editor |= visible && enabled && cls.ToString() == "wxWindowClassNR" &&
                    title.ToString().StartsWith("Terrain Builder", StringComparison.Ordinal);
                dialog |= visible && (cls.ToString() == "#32770" || title.ToString().Contains("TerrainBuilder Error"));
                if (visible)
                {
                    try
                    {
                        var root = AutomationElement.FromHandle(window);
                        Walk(root, pid, window.ToInt64(), "", 0, ref budget, timer, ref errors);
                        uia = true;
                    }
                    catch (Exception e) { Console.WriteLine("UIA unavailable: {0}", e.GetType().Name); }
                }
                return true;
            }, IntPtr.Zero);
            if (!enumerated) throw LastError("EnumDesktopWindows");
            Console.WriteLine("nodes={0}; UIAErrors={1}; elapsedMs={2}", 500 - budget, errors, timer.ElapsedMilliseconds);
            found.Refresh();
            if (found.HasExited) { Console.WriteLine("Process exited during inspection."); return 3; }
            Console.WriteLine("editorWindow={0}; dialogObserved={1}; uia={2}; responding={3}", editor, dialog, uia, found.Responding);
            return editor && !dialog && uia && found.Responding ? 0 : 4;
        }
    }

    private static void Walk(AutomationElement element, int pid, long hwnd, string parent, int depth,
        ref int budget, Stopwatch timer, ref int errors)
    {
        if (element == null || budget <= 0 || timer.ElapsedMilliseconds >= 9000) return;
        var info = element.Current;
        if (info.ProcessId != pid) return;
        budget--;
        string id = String.Join(".", element.GetRuntimeId().Select(n => n.ToString()).ToArray());
        var patterns = element.GetSupportedPatterns();
        var readable = new System.Collections.Generic.Dictionary<string, object>();
        foreach (var pattern in patterns)
        {
            object value;
            try
            {
                if (!element.TryGetCurrentPattern(pattern, out value)) continue;
                if (value is ExpandCollapsePattern) readable["expandState"] = ((ExpandCollapsePattern)value).Current.ExpandCollapseState.ToString();
                if (value is SelectionItemPattern) readable["selected"] = ((SelectionItemPattern)value).Current.IsSelected;
                if (value is SelectionPattern) readable["multiSelect"] = ((SelectionPattern)value).Current.CanSelectMultiple;
                if (value is ValuePattern) readable["valueReadOnly"] = ((ValuePattern)value).Current.IsReadOnly;
                if (value is WindowPattern) readable["windowState"] = ((WindowPattern)value).Current.WindowVisualState.ToString();
                if (value is TextPattern) readable["textSelection"] = ((TextPattern)value).SupportedTextSelection.ToString();
            }
            catch (Exception e) { errors++; readable[pattern.ProgrammaticName] = e.GetType().Name; }
        }
        Console.WriteLine(Json.Serialize(new { pid, hwnd, id, parent, depth, name = info.IsPassword ? "" : info.Name,
            automationId = info.AutomationId, cls = info.ClassName, framework = info.FrameworkId,
            type = info.ControlType.ProgrammaticName, enabled = info.IsEnabled, offscreen = info.IsOffscreen,
            focusable = info.IsKeyboardFocusable, password = info.IsPassword,
            patterns = patterns.Select(p => p.ProgrammaticName).ToArray(), readable }));
        if (depth >= 10) return;
        var walker = TreeWalker.RawViewWalker;
        for (var child = walker.GetFirstChild(element); child != null && budget > 0 && timer.ElapsedMilliseconds < 9000;
             child = walker.GetNextSibling(child))
            Walk(child, pid, hwnd, id, depth + 1, ref budget, timer, ref errors);
    }

    private static IntPtr OpenDefault()
    {
        int session = Process.GetCurrentProcess().SessionId;
        string current = Desktop();
        Console.WriteLine("session={0}; console={1}; parentDesktop={2}", session, WTSGetActiveConsoleSessionId(), current);
        if (session == 0 || session != WTSGetActiveConsoleSessionId() ||
            !current.StartsWith(@"WinSta0\", StringComparison.Ordinal))
            throw new InvalidOperationException("Active console window station unavailable.");
        IntPtr input = OpenInputDesktop(0, false, 1);
        if (input == IntPtr.Zero) throw LastError("OpenInputDesktop");
        try
        {
            if (!IsTarget(@"WinSta0\" + Name(input))) throw new InvalidOperationException("Default is not active.");
        }
        finally { CloseDesktop(input); }
        IntPtr desktop = OpenDesktop("Default", 0, false, 1);
        if (desktop == IntPtr.Zero) throw LastError("OpenDesktopW(Default)");
        return desktop;
    }

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            string home = AppDomain.CurrentDomain.BaseDirectory;
            if (args.Length == 5 && args[0] == "child")
            {
                Guid id = Guid.ParseExact(args[1], "N");
                string log = Path.Combine(home, id.ToString("N"), "CHILD.log");
                using (var writer = NewLog(log))
                {
                    Console.SetOut(writer);
                    string actual = Desktop();
                    Console.WriteLine("childDesktop={0}", actual);
                    if (!IsTarget(actual)) return 2;
                    if (args[2] == "probe") return 0;
                    if (args[2] != "status") return 64;
                    IntPtr desktop = OpenDefault();
                    try { return Inspect(Int32.Parse(args[3]), Int64.Parse(args[4]), desktop); }
                    finally { CloseDesktop(desktop); }
                }
            }
            if (args.Length == 0 || (args[0] == "uia-inventory" ? args.Length != 3 :
                args.Length != 1 || (args[0] != "self-test"))) return 64;
            string nonce = Guid.NewGuid().ToString("N");
            string dir = Directory.CreateDirectory(Path.Combine(home, nonce)).FullName;
            Console.WriteLine("evidence={0}", dir);
            using (var journal = NewLog(Path.Combine(dir, "PARENT.log")))
            {
                Console.SetOut(journal);
                if (args[0] == "self-test") return SelfTest(dir);
                IntPtr desktop = OpenDefault();
                try
                {
                    string suffix = " probe 0 0";
                    if (args[0] == "uia-inventory")
                        suffix = " status " + Int32.Parse(args[1]) + " " + Int64.Parse(args[2]);
                    ProcessInfo child = Launch(typeof(UiaInventory).Assembly.Location, " child " + nonce + suffix);
                    try
                    {
                        Console.WriteLine("childPid={0}", child.Pid);
                        uint wait = WaitForSingleObject(child.Process, 12000);
                        if (wait == 0xFFFFFFFF) throw LastError("WaitForSingleObject(child)");
                        if (wait != 0) { Console.WriteLine("Diagnostic wait result={0}", wait); return WaitResult(wait); }
                        uint exit;
                        if (!GetExitCodeProcess(child.Process, out exit)) throw LastError("GetExitCodeProcess(child)");
                        Console.WriteLine("childExit={0}", exit);
                        return (int)exit;
                    }
                    finally { CloseHandle(child.Process); }
                }
                finally { CloseDesktop(desktop); }
            }
        }
        catch (Exception e)
        {
            var win32 = e as Win32Exception;
            Console.Error.WriteLine("BLOCKED: {0}{1}", e.Message, win32 == null ? "" : "; Win32=" + win32.NativeErrorCode);
            return 2;
        }
    }
}
