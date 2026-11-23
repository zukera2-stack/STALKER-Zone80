using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Windows.Automation;

internal static class DefaultLauncher
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

    private static bool CanLaunch(int instances) { return instances == 0; }
    private static bool IsTarget(string desktop) { return desktop == Target; }

    private static StreamWriter NewLog(string path)
    {
        return new StreamWriter(new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read)) { AutoFlush = true };
    }

    private static int SelfTest(string dir)
    {
        if (!Matches("TerrainBuilder", ExpectedExe(), 1, 1, ExpectedHash) ||
            Matches("TerrainBuilder", ExpectedExe(), 1, 1, "bad") ||
            Matches("TerrainBuilder", ExpectedExe(), 2, 1, ExpectedHash) ||
            Matches("foreign", ExpectedExe(), 1, 1, ExpectedHash) ||
            Matches("TerrainBuilder", ExpectedExe() + ".other", 1, 1, ExpectedHash) ||
            CanLaunch(1) || !CanLaunch(0) || IsTarget("unavailable") || !IsTarget(Target))
            throw new InvalidOperationException("Guard self-test failed.");
        string path = Path.Combine(dir, "collision.txt");
        using (var log = NewLog(path)) log.WriteLine("original");
        bool refused = false;
        try { using (NewLog(path)) { } }
        catch (IOException) { refused = true; }
        if (!refused || File.ReadAllText(path).Trim() != "original")
            throw new InvalidOperationException("Existing log was not preserved.");
        Console.WriteLine("PASS: identity, reused PID, SHA, path, foreign instance, desktop and existing log guards");
        return Inspect(Int32.MaxValue, 1, IntPtr.Zero) == 3 ? 0 : 2;
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
            bool enumerated = EnumDesktopWindows(desktop, delegate(IntPtr window, IntPtr ignored)
            {
                uint owner;
                GetWindowThreadProcessId(window, out owner);
                if (owner != (uint)pid) return true;
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
                        int budget = 120;
                        Walk(root, 0, ref budget);
                        uia = true;
                    }
                    catch (Exception e) { Console.WriteLine("UIA unavailable: {0}", e.GetType().Name); }
                }
                return true;
            }, IntPtr.Zero);
            if (!enumerated) throw LastError("EnumDesktopWindows");
            found.Refresh();
            if (found.HasExited) { Console.WriteLine("Process exited during inspection."); return 3; }
            Console.WriteLine("editorWindow={0}; dialogObserved={1}; uia={2}; responding={3}", editor, dialog, uia, found.Responding);
            return editor && !dialog && uia && found.Responding ? 0 : 4;
        }
    }

    private static void Walk(AutomationElement element, int depth, ref int budget)
    {
        if (element == null || budget <= 0) return;
        budget--;
        var info = element.Current;
        Console.WriteLine("{0}{1}; name={2}; enabled={3}; offscreen={4}", new string(' ', depth * 2),
            info.ControlType.ProgrammaticName, info.Name, info.IsEnabled, info.IsOffscreen);
        if (depth == 5) return;
        var walker = TreeWalker.ControlViewWalker;
        for (var child = walker.GetFirstChild(element); child != null && budget > 0; child = walker.GetNextSibling(child))
            Walk(child, depth + 1, ref budget);
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
            if (args.Length == 0 || (args[0] == "status" ? args.Length != 3 :
                args.Length != 1 || (args[0] != "run" && args[0] != "probe" && args[0] != "self-test"))) return 64;
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
                    if (args[0] == "status")
                        suffix = " status " + Int32.Parse(args[1]) + " " + Int64.Parse(args[2]);
                    ProcessInfo child = Launch(typeof(DefaultLauncher).Assembly.Location, " child " + nonce + suffix);
                    try
                    {
                        Console.WriteLine("childPid={0}", child.Pid);
                        uint wait = WaitForSingleObject(child.Process, 12000);
                        if (wait == 0xFFFFFFFF) throw LastError("WaitForSingleObject(child)");
                        if (wait != 0) throw new InvalidOperationException("Diagnostic child timed out.");
                        uint exit;
                        if (!GetExitCodeProcess(child.Process, out exit)) throw LastError("GetExitCodeProcess(child)");
                        Console.WriteLine("childExit={0}", exit);
                        if (args[0] != "run" || exit != 0) return (int)exit;
                    }
                    finally { CloseHandle(child.Process); }
                    using (var mutex = new Mutex(false, @"Local\STALKER-Zone80-TerrainBuilder-Launch"))
                    {
                        bool owned;
                        try { owned = mutex.WaitOne(0); }
                        catch (AbandonedMutexException) { owned = true; }
                        if (!owned) throw new InvalidOperationException("Another launcher holds the mutex.");
                        try
                        {
                            string exe = ExpectedExe();
                            if (Hash(exe) != ExpectedHash) throw new InvalidOperationException("Terrain Builder SHA mismatch.");
                            foreach (string name in new[] { "TerrainBuilder", "TerrainBuilderNew" })
                            {
                                var instances = Process.GetProcessesByName(name);
                                foreach (var instance in instances) instance.Dispose();
                                if (!CanLaunch(instances.Length)) throw new InvalidOperationException("Terrain Builder already running.");
                            }
                            ProcessInfo launched = Launch(exe, "");
                            CloseHandle(launched.Process);
                            Console.WriteLine("LAUNCHED_UNVERIFIED pid={0}; utc={1:o}", launched.Pid, DateTime.UtcNow);
                            return 0;
                        }
                        finally { mutex.ReleaseMutex(); }
                    }
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
