using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

internal static class D3D9Probe
{
    [StructLayout(LayoutKind.Sequential)]
    private struct PresentParameters
    {
        public uint Width, Height, Format, Count, MultiSample, Quality, SwapEffect;
        public IntPtr Window;
        public int Windowed, AutoDepthStencil;
        public uint DepthFormat, Flags, RefreshRate, Interval;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)]
    private struct Adapter
    {
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 512)] public string Driver;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 512)] public string Description;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string DeviceName;
        public long DriverVersion;
        public uint Vendor, Device, SubSystem, Revision;
        public Guid Identifier;
        public uint Whql;
    }

    [UnmanagedFunctionPointer(CallingConvention.StdCall)] private delegate uint Count(IntPtr self);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] private delegate int Identify(IntPtr self, uint index, uint flags, out Adapter adapter);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] private delegate int DisplayMode(IntPtr self, uint index, out Mode mode);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] private delegate int Check(IntPtr self, uint index, uint type, uint screen, uint buffer, int windowed);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] private delegate int Create(IntPtr self, uint index, uint type, IntPtr focus, uint flags, ref PresentParameters parameters, out IntPtr device);

    [StructLayout(LayoutKind.Sequential)]
    private struct Mode { public uint Width, Height, Refresh, Format; }

    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern IntPtr LoadLibraryEx(string name, IntPtr file, uint flags);
    [DllImport("kernel32.dll")] private static extern bool FreeLibrary(IntPtr module);
    [DllImport("kernel32.dll", ExactSpelling = true)] private static extern IntPtr GetProcAddress(IntPtr module, string name);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] private delegate IntPtr CreateInterface(uint version);
    [DllImport("kernel32.dll")] private static extern uint WTSGetActiveConsoleSessionId();
    [DllImport("wtsapi32.dll", EntryPoint = "WTSQuerySessionInformationW", SetLastError = true)]
    private static extern bool QuerySession(IntPtr server, int session, int field, out IntPtr data, out int bytes);
    [DllImport("wtsapi32.dll")] private static extern void WTSFreeMemory(IntPtr memory);
    [DllImport("user32.dll")] private static extern IntPtr GetProcessWindowStation();
    [DllImport("kernel32.dll")] private static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] private static extern IntPtr GetThreadDesktop(uint thread);
    [DllImport("user32.dll", SetLastError = true)] private static extern IntPtr OpenInputDesktop(uint flags, bool inherit, uint access);
    [DllImport("user32.dll")] private static extern bool CloseDesktop(IntPtr desktop);
    [DllImport("user32.dll", EntryPoint = "GetUserObjectInformationW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ObjectName(IntPtr handle, int index, StringBuilder value, int size, out int needed);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateWindowEx(uint exStyle, string cls, string title, uint style, int x, int y, int w, int h,
        IntPtr parent, IntPtr menu, IntPtr instance, IntPtr parameter);
    [DllImport("user32.dll")] private static extern bool IsWindow(IntPtr hwnd);
    [DllImport("user32.dll")] private static extern bool DestroyWindow(IntPtr hwnd);

    private static string Name(IntPtr handle)
    {
        int size;
        var name = new StringBuilder(256);
        return handle != IntPtr.Zero && ObjectName(handle, 2, name, name.Capacity * 2, out size) ? name.ToString() : "";
    }

    private static int SessionField(int session, int field, int size)
    {
        IntPtr data;
        int bytes;
        if (!QuerySession(IntPtr.Zero, session, field, out data, out bytes)) return -1;
        try { return bytes < size ? -1 : size == 2 ? Marshal.ReadInt16(data) : Marshal.ReadInt32(data); }
        finally { WTSFreeMemory(data); }
    }

    private static string Hex(int value) { return "0x" + unchecked((uint)value).ToString("X8"); }

    private static T Method<T>(IntPtr obj, int slot) where T : class
    {
        IntPtr entry = Marshal.ReadIntPtr(Marshal.ReadIntPtr(obj), slot * IntPtr.Size);
        return (T)(object)Marshal.GetDelegateForFunctionPointer(entry, typeof(T));
    }

    private static int Main(string[] args)
    {
        if (args.Length == 1 && args[0] == "--self-test")
        {
            int expected = IntPtr.Size == 4 ? 56 : 64;
            if (Marshal.SizeOf(typeof(PresentParameters)) != expected ||
                Marshal.OffsetOf(typeof(PresentParameters), "Window").ToInt32() != (IntPtr.Size == 4 ? 28 : 32) ||
                Marshal.SizeOf(typeof(Adapter)) != 1104 ||
                Marshal.OffsetOf(typeof(Adapter), "DriverVersion").ToInt32() != 1056 ||
                Hex(unchecked((int)0x8876086C)) != "0x8876086C" || Hex(0) != "0x00000000")
                return 1;
            Console.WriteLine("PASS: native struct ABI and HRESULT formatting");
            return 0;
        }
        if (args.Length != 0) return 64;
        int session = Process.GetCurrentProcess().SessionId;
        int protocol = SessionField(session, 16, 2);
        int state = SessionField(session, 8, 4);
        string station = Name(GetProcessWindowStation());
        string threadDesktop = Name(GetThreadDesktop(GetCurrentThreadId()));
        IntPtr input = OpenInputDesktop(0, false, 1);
        int desktopError = input == IntPtr.Zero ? Marshal.GetLastWin32Error() : 0;
        string inputDesktop = Name(input);
        if (input != IntPtr.Zero) CloseDesktop(input);
        Console.WriteLine("bits={0}; session={1}; consoleSession={2}; protocol={3}; state={4}; station={5}; threadDesktop={6}; inputDesktop={7}; inputError={8}",
            IntPtr.Size * 8, session, WTSGetActiveConsoleSessionId(), protocol, state, station, threadDesktop, inputDesktop, desktopError);
        if (session == 0 || station != "WinSta0" || threadDesktop != "Default" || inputDesktop != threadDesktop ||
            (state != 0 && !(state == -1 && session == WTSGetActiveConsoleSessionId())))
        {
            Console.WriteLine("BLOCKED: active interactive desktop not established");
            return 2;
        }
        IntPtr module = LoadLibraryEx("d3d9.dll", IntPtr.Zero, 0x800);
        if (module == IntPtr.Zero)
        {
            Console.WriteLine("BLOCKED: system d3d9.dll load Win32 error {0}", Marshal.GetLastWin32Error());
            return 2;
        }
        IntPtr hwnd = IntPtr.Zero, d3d = IntPtr.Zero;
        try
        {
            hwnd = CreateWindowEx(0x08000000, "STATIC", "D3D9 diagnostic", 0x80000000, 0, 0, 64, 64,
                IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero);
            if (hwnd == IntPtr.Zero || !IsWindow(hwnd))
            {
                Console.WriteLine("BLOCKED: own HWND unavailable; Win32 error {0}", Marshal.GetLastWin32Error());
                return 2;
            }
            Console.WriteLine("ownHwnd=0x{0:X}", hwnd.ToInt64());
            IntPtr factory = GetProcAddress(module, "Direct3DCreate9");
            if (factory == IntPtr.Zero) return 2;
            d3d = ((CreateInterface)Marshal.GetDelegateForFunctionPointer(factory, typeof(CreateInterface)))(32);
            Console.WriteLine("Direct3DCreate9={0} (pointer API, no HRESULT)", d3d == IntPtr.Zero ? "NULL" : "non-NULL");
            if (d3d == IntPtr.Zero) return 3;
            uint count = Method<Count>(d3d, 4)(d3d);
            Console.WriteLine("GetAdapterCount={0} (count API, no HRESULT)", count);
            bool accessible = false;
            for (uint i = 0; i < count; i++)
            {
                Adapter adapter;
                int hr = Method<Identify>(d3d, 5)(d3d, i, 0, out adapter);
                Console.WriteLine("adapter={0}; GetAdapterIdentifier={1}; name={2}; driver={3}; vendor=0x{4:X4}; device=0x{5:X4}",
                    i, Hex(hr), adapter.Description, adapter.Driver, adapter.Vendor, adapter.Device);
                Mode mode;
                hr = Method<DisplayMode>(d3d, 8)(d3d, i, out mode);
                Console.WriteLine("adapter={0}; GetAdapterDisplayMode={1}; format={2}", i, Hex(hr), mode.Format);
                if (hr < 0) continue;
                hr = Method<Check>(d3d, 9)(d3d, i, 1, mode.Format, 0, 1);
                Console.WriteLine("adapter={0}; CheckDeviceType(HAL)={1}", i, Hex(hr));
                var pp = new PresentParameters { Width = 64, Height = 64, Count = 1, SwapEffect = 1,
                    Window = hwnd, Windowed = 1, Interval = 0 };
                IntPtr device;
                hr = Method<Create>(d3d, 16)(d3d, i, 1, hwnd, 0x20, ref pp, out device);
                Console.WriteLine("adapter={0}; CreateDevice(HAL, windowed, software vertex processing)={1}; device={2}",
                    i, Hex(hr), device == IntPtr.Zero ? "NULL" : "non-NULL");
                if (device != IntPtr.Zero)
                {
                    accessible |= hr >= 0;
                    Marshal.Release(device);
                }
            }
            return accessible ? 0 : 3;
        }
        finally
        {
            if (d3d != IntPtr.Zero) Marshal.Release(d3d);
            if (hwnd != IntPtr.Zero) DestroyWindow(hwnd);
            FreeLibrary(module);
        }
    }
}
