# Zone80: semantic import-toolbar invocation. Default is read-only planning.
param(
 [Parameter(Mandatory=$true)][int]$TargetPid,
 [Parameter(Mandatory=$true)][long]$StartedUtcTicks,
 [Parameter(Mandatory=$true)][string]$ExecutableSha256,
 [Parameter(Mandatory=$true)][string]$ExpectedTitle,
 [ValidateSet('terrain','satellite','mask','shapes','objects')][string]$Layer='satellite',
 [switch]$Execute
)
$ErrorActionPreference='Stop'
$tb=Get-Process -Id $TargetPid
if($tb.ProcessName -ne 'TerrainBuilder' -or $tb.StartTime.ToUniversalTime().Ticks -ne $StartedUtcTicks -or $tb.MainWindowTitle -cne $ExpectedTitle -or (Get-FileHash -LiteralPath $tb.Path).Hash -ne $ExecutableSha256){throw 'Target identity mismatch'}
if(Get-Process -Name UiaAction,UiaInventory -ErrorAction SilentlyContinue){throw 'Concurrent UIA action'}
Add-Type -AssemblyName Accessibility,UIAutomationClient,UIAutomationTypes,WindowsBase
$refs=@([Accessibility.IAccessible].Assembly.Location,[System.Windows.Automation.AutomationElement].Assembly.Location,[System.Windows.Automation.AutomationIdentifier].Assembly.Location,[System.Windows.Rect].Assembly.Location)
Add-Type -ReferencedAssemblies $refs -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using Accessibility;
using System.Windows.Automation;
public static class Zone80TbImport {
 [DllImport("oleacc.dll")] static extern int AccessibleObjectFromWindow(IntPtr hwnd,uint obj,ref Guid iid,[MarshalAs(UnmanagedType.Interface)] out IAccessible acc);
 [DllImport("oleacc.dll")] static extern int AccessibleChildren(IAccessible acc,int start,int count,[Out,MarshalAs(UnmanagedType.LPArray,SizeParamIndex=2)] object[] items,out int got);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint pid);
 [DllImport("user32.dll")] static extern IntPtr GetParent(IntPtr hwnd);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr hwnd,System.Text.StringBuilder text,int n);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr hwnd,System.Text.StringBuilder text,int n);
 [DllImport("user32.dll")] static extern bool IsWindowEnabled(IntPtr hwnd);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr hwnd);
 delegate bool EnumProc(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f,IntPtr p);
 static bool Owned(IntPtr h,int pid){uint q;GetWindowThreadProcessId(h,out q);return q==(uint)pid;}
 static string Name(IntPtr h){var b=new System.Text.StringBuilder(512);GetWindowText(h,b,b.Capacity);return b.ToString();}
 static string Class(IntPtr h){var b=new System.Text.StringBuilder(256);GetClassName(h,b,b.Capacity);return b.ToString();}
 static bool Clear(IntPtr main,int pid){bool blocked=false;bool ok=EnumWindows(delegate(IntPtr k,IntPtr p){if(k!=main&&Owned(k,pid)&&IsWindowVisible(k)){var c=Class(k);if(c=="#32770"||c=="#32768")blocked=true;}return true;},IntPtr.Zero);return ok&&!blocked;}
 public static void Run(long frame,int pid,string title,string label,bool execute){
 var main=new IntPtr(frame);if(!Owned(main,pid)||!IsWindowEnabled(main)||!IsWindowVisible(main)||Name(main)!=title||!Clear(main,pid))throw new InvalidOperationException("Main window or modal state mismatch");
 var root=AutomationElement.FromHandle(main);var toolbars=root.FindAll(TreeScope.Descendants,new PropertyCondition(AutomationElement.NameProperty,"ImportToolBar"));AutomationElement toolbar=null;int nh=0;
 foreach(AutomationElement e in toolbars){if(e.Current.ProcessId==pid&&e.Current.IsEnabled&&!e.Current.IsOffscreen){toolbar=e;nh++;}}
 if(nh!=1)throw new InvalidOperationException("Import toolbar not unique");
 var native=toolbar.FindAll(TreeScope.Descendants,new PropertyCondition(AutomationElement.ClassNameProperty,"ToolbarWindow32"));IntPtr h=IntPtr.Zero;nh=0;
 foreach(AutomationElement e in native){var c=e.Current;var k=new IntPtr(c.NativeWindowHandle);if(k!=IntPtr.Zero&&c.ProcessId==pid&&c.IsEnabled&&!c.IsOffscreen&&Owned(k,pid)&&Class(k)=="ToolbarWindow32"&&Name(GetParent(k))=="ImportToolBar"){h=k;nh++;}}
 if(nh!=1||!IsWindowVisible(h)||!IsWindowEnabled(h)||!Owned(GetParent(h),pid))throw new InvalidOperationException("Native toolbar not unique");
 var list=AutomationElement.FromHandle(h).FindAll(TreeScope.Children,Condition.TrueCondition);AutomationElement ui=null;nh=0;
 foreach(AutomationElement e in list){var c=e.Current;if(c.ProcessId==pid&&c.Name==label&&c.IsEnabled&&!c.IsOffscreen){ui=e;nh++;}}
 if(nh!=1||list.Count!=6)throw new InvalidOperationException("Named target or toolbar structure mismatch");
 var rect=ui.Current.BoundingRectangle;
 Guid iid=new Guid("618736E0-3C3D-11CF-810C-00AA00389B71");IAccessible a;int hr=AccessibleObjectFromWindow(h,0xFFFFFFFC,ref iid,out a);if(hr!=0||a==null||a.accChildCount!=6)throw new InvalidOperationException("MSAA toolbar unavailable");
 object[] items=new object[6];int got;if(AccessibleChildren(a,0,6,items,out got)!=0||got!=6)throw new InvalidOperationException("MSAA children mismatch");IAccessible selected=null;object selectedId=null;nh=0;
 for(int i=0;i<got;i++){var c=items[i];IAccessible child=c as IAccessible;IAccessible t=child??a;object id=child!=null?(object)0:c;int x,y,w,ht;t.accLocation(out x,out y,out w,out ht,id);if(x==rect.X&&y==rect.Y&&w==rect.Width&&ht==rect.Height){if(Convert.ToInt32(t.get_accRole(id))!=43||Convert.ToInt32(t.get_accState(id))!=0||String.IsNullOrEmpty(t.get_accDefaultAction(id)))throw new InvalidOperationException("MSAA button unavailable");selected=t;selectedId=id;nh++;}}
 if(nh!=1)throw new InvalidOperationException("Semantic mapping ambiguous");
 Console.WriteLine("CROSSCHECK unique owned toolbar: "+label);
 if(!execute){Console.WriteLine("PLAN_ONLY");return;}
 if(!Clear(main,pid)||Name(main)!=title||!Owned(h,pid)||!IsWindowEnabled(main))throw new InvalidOperationException("State changed before action");
 selected.accDoDefaultAction(selectedId);Console.WriteLine("ACTION_RETURNED; verify expected dialog independently before continuing");
 }
}
'@
$labels=@{terrain='Import terrain...';satellite='Import satellite...';mask='Import surface mask...';shapes='Import shapes...';objects='Import objects...'}
[Zone80TbImport]::Run($tb.MainWindowHandle.ToInt64(),$TargetPid,$ExpectedTitle,$labels[$Layer],$Execute.IsPresent)
