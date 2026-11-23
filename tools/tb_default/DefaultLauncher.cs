using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

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
    [DllImport("user32.dll")] private static extern bool EnumDesktopWindows(IntPtr desktop, WindowCallback callback, IntPtr param);
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

    private static int Main(string[] args)
    {
        try
        {
            if (args.Length == 1 && args[0] == "child-probe")
            {
                string observed = Desktop();
                File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "CHILD.txt"), observed);
                return observed == Target ? 0 : 2;
            }
            if (args.Length != 1 || args[0] != "run") return 64;
            int session = Process.GetCurrentProcess().SessionId;
            uint console = WTSGetActiveConsoleSessionId();
            string current = Desktop();
            Console.WriteLine("session={0}; console={1}; parentDesktop={2}", session, console, current);
            if (session == 0 || session != console || !current.StartsWith(@"WinSta0\", StringComparison.Ordinal))
                throw new InvalidOperationException("Parent is outside the active console window station.");

            IntPtr input = OpenInputDesktop(0, false, 1);
            if (input == IntPtr.Zero) throw LastError("OpenInputDesktop");
            try
            {
                string name = Name(input);
                Console.WriteLine("inputDesktop={0}", name);
                if (name != "Default") throw new InvalidOperationException("Default is not the input desktop.");
            }
            finally { CloseDesktop(input); }

            IntPtr desktop = OpenDesktop("Default", 0, false, 1);
            if (desktop == IntPtr.Zero) throw LastError("OpenDesktopW(Default, DESKTOP_READOBJECTS)");
            try
            {
                string childLog = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "CHILD.txt");
                if (File.Exists(childLog)) throw new InvalidOperationException("Prior child probe exists.");
                ProcessInfo child = Launch(typeof(DefaultLauncher).Assembly.Location, " child-probe");
                try
                {
                    Console.WriteLine("childPid={0}", child.Pid);
                    uint wait = WaitForSingleObject(child.Process, 5000);
                    if (wait == 0xFFFFFFFF) throw LastError("WaitForSingleObject(child)");
                    if (wait != 0) throw new InvalidOperationException("Child probe timed out.");
                    uint exit;
                    if (!GetExitCodeProcess(child.Process, out exit)) throw LastError("GetExitCodeProcess(child)");
                    if (!File.Exists(childLog)) throw new InvalidOperationException("Child desktop evidence missing.");
                    string actual = File.ReadAllText(childLog);
                    Console.WriteLine("childDesktop={0}; childExit={1}", actual, exit);
                    if (exit != 0 || actual != Target) throw new InvalidOperationException("Child desktop mismatch.");
                }
                finally { CloseHandle(child.Process); }

                string exe = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                    @"Steam\steamapps\common\Arma 3 Tools\TerrainBuilder\TerrainBuilder.exe");
                using (var sha = SHA256.Create())
                using (var file = File.OpenRead(exe))
                {
                    string hash = BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "");
                    Console.WriteLine("exeSha256={0}", hash);
                    if (hash != ExpectedHash) throw new InvalidOperationException("Terrain Builder SHA-256 mismatch.");
                }
                foreach (string name in new[] { "TerrainBuilder", "TerrainBuilderNew" })
                    if (Process.GetProcessesByName(name).Length != 0)
                        throw new InvalidOperationException("Terrain Builder is already running.");

                ProcessInfo launched = Launch(exe, "");
                uint pid = launched.Pid;
                CloseHandle(launched.Process);
                Console.WriteLine("LAUNCHED_UNVERIFIED; pid={0}; utc={1:o}", pid, DateTime.UtcNow);
                using (var process = Process.GetProcessById((int)pid))
                {
                    var elapsed = Stopwatch.StartNew();
                    while (elapsed.ElapsedMilliseconds < 9500)
                    {
                        process.Refresh();
                        if (process.HasExited) { Console.WriteLine("exit={0}", process.ExitCode); break; }
                        Console.WriteLine("utc={0:o}; workingSet={1}; privateBytes={2}; responding={3}", DateTime.UtcNow,
                            process.WorkingSet64, process.PrivateMemorySize64, process.Responding);
                        bool enumerated = EnumDesktopWindows(desktop, delegate(IntPtr window, IntPtr ignored)
                        {
                            uint owner;
                            uint thread = GetWindowThreadProcessId(window, out owner);
                            if (owner != pid) return true;
                            var title = new StringBuilder(256);
                            var cls = new StringBuilder(256);
                            GetWindowText(window, title, title.Capacity);
                            GetClassName(window, cls, cls.Capacity);
                            Console.WriteLine("hwnd=0x{0:X}; thread={1}; visible={2}; class={3}; title={4}", window.ToInt64(),
                                thread, IsWindowVisible(window), cls, title);
                            return true;
                        }, IntPtr.Zero);
                        if (!enumerated) Console.WriteLine("windowEnumeration=unavailable");
                        Thread.Sleep(500);
                    }
                }
                return 0;
            }
            finally { CloseDesktop(desktop); }
        }
        catch (Win32Exception e)
        {
            Console.WriteLine("BLOCKED: {0}; Win32Error={1} (0x{1:X8})", e.Message, e.NativeErrorCode);
            return 2;
        }
        catch (Exception e)
        {
            Console.WriteLine("BLOCKED: {0}", e.Message);
            return 2;
        }
    }
}
