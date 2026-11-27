"""Zone80 read-only Terrain Builder Win32 inventory and fail-closed action planning.
Inspired by the DayZ runner's approach, independently implemented; no action dispatch.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import sys
import unittest

def normalize(s):
    return s.replace("&&", "\x00").replace("&", "").replace("\x00", "&").split("\t")[0].strip().casefold()

def select_menu(rows, path):
    key = [normalize(x) for x in path]
    hits = [r for r in rows if [normalize(x) for x in r["path"]] == key]
    if len(hits) != 1:
        raise ValueError("menu missing or ambiguous")
    r = hits[0]
    if r.get("disabled") or r.get("separator") or r.get("ownerdraw") or r.get("submenu") or r.get("error"):
        raise ValueError("menu not actionable")
    if not isinstance(r.get("id"), int) or not 1 <= r["id"] <= 65535:
        raise ValueError("invalid command ID")
    return {"status":"PLAN_ONLY", "path":r["path"], "observed_id":r["id"], "must_revalidate":True}

def select_button(rows, label):
    hits = [r for r in rows if r.get("class","").casefold()=="button"
            and normalize(r.get("title",""))==normalize(label)
            and r.get("visible") and r.get("enabled")]
    if len(hits)!=1:
        raise ValueError("button missing or ambiguous")
    return {"status":"PLAN_ONLY", "label":hits[0]["title"], "observed_id":hits[0]["id"], "must_revalidate":True}

def inventory(pid):
    if sys.platform != "win32":
        raise RuntimeError("native inventory requires Windows")
    u=C.WinDLL("user32", use_last_error=True)
    cb=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    def bind(n,rest,args):
        f=getattr(u,n); f.restype=rest; f.argtypes=args; return f
    enum=bind("EnumWindows",W.BOOL,[cb,W.LPARAM])
    children=bind("EnumChildWindows",W.BOOL,[W.HWND,cb,W.LPARAM])
    owner=bind("GetWindowThreadProcessId",W.DWORD,[W.HWND,C.POINTER(W.DWORD)])
    title=bind("GetWindowTextW",C.c_int,[W.HWND,W.LPWSTR,C.c_int])
    cls=bind("GetClassNameW",C.c_int,[W.HWND,W.LPWSTR,C.c_int])
    vis=bind("IsWindowVisible",W.BOOL,[W.HWND])
    enabled=bind("IsWindowEnabled",W.BOOL,[W.HWND])
    ident=bind("GetDlgCtrlID",C.c_int,[W.HWND])
    menu=bind("GetMenu",W.HMENU,[W.HWND])
    count=bind("GetMenuItemCount",C.c_int,[W.HMENU])
    sub=bind("GetSubMenu",W.HMENU,[W.HMENU,C.c_int])
    state=bind("GetMenuState",W.UINT,[W.HMENU,W.UINT,W.UINT])
    mid=bind("GetMenuItemID",W.UINT,[W.HMENU,C.c_int])
    mtext=bind("GetMenuStringW",C.c_int,[W.HMENU,W.UINT,W.LPWSTR,C.c_int,W.UINT])
    def belongs(h):
        p=W.DWORD(); owner(h,C.byref(p)); return p.value==pid
    def describe(h):
        t=C.create_unicode_buffer(512); c=C.create_unicode_buffer(128)
        title(h,t,len(t)); cls(h,c,len(c))
        return {"hwnd":int(h),"class":c.value,"title":t.value,
                "visible":bool(vis(h)),"enabled":bool(enabled(h)),"id":ident(h)}
    def walk(m,path=(),depth=0):
        if not m or depth>10:return []
        out=[]
        for i in range(min(max(count(m),0),500)):
            b=C.create_unicode_buffer(512); mtext(m,i,b,len(b),0x400)
            s=state(m,i,0x400); child=sub(m,i)
            label=b.value or "#"+str(i)
            row={"path":list(path)+( [label]),"id":mid(m,i),
                 "disabled":bool(s&3),"separator":bool(s&0x800),
                 "ownerdraw":bool(s&0x100),"submenu":bool(child),
                 "error":s==0xffffffff}
            out.append(row)
            if child:out.extend(walk(child,tuple(row["path"]),depth+1))
        return out
    tops=[]
    @cb
    def collect(h,_):
        if belongs(h) and vis(h):tops.append(h)
        return True
    if not enum(collect,0):raise RuntimeError("EnumWindows failed")
    windows=[]
    for h in tops:
        if not belongs(h):continue
        row=describe(h); row["menu"]=walk(menu(h)); row["children"]=[]
        @cb
        def child_cb(k,_):
            if belongs(k) and len(row["children"])<500:row["children"].append(describe(k))
            return True
        children(h,child_cb,0)
        windows.append(row)
    return {"status":"READ_ONLY","pid":pid,"windows":windows,
            "note":"GetWindowTextW does not prove cross-process edit values; menu state may be stale. No messages dispatched."}

class Tests(unittest.TestCase):
    def setUp(self):
        self.row={"path":["&File","&Save As..."],"id":123,"disabled":False}
    def test_exact(self):self.assertEqual(select_menu([self.row],["File","Save As..."])["observed_id"],123)
    def test_duplicate(self):
        with self.assertRaises(ValueError):select_menu([self.row,self.row],["File","Save As..."])
    def test_disabled(self):
        with self.assertRaises(ValueError):select_menu([dict(self.row,disabled=True)],["File","Save As..."])
    def test_bad_id(self):
        with self.assertRaises(ValueError):select_menu([dict(self.row,id=4294967295)],["File","Save As..."])
    def test_ownerdraw(self):
        with self.assertRaises(ValueError):select_menu([dict(self.row,ownerdraw=True)],["File","Save As..."])
    def test_submenu(self):
        with self.assertRaises(ValueError):select_menu([dict(self.row,submenu=True)],["File","Save As..."])
    def test_button_swap(self):
        rows=[{"class":"Button","title":"OK","id":2,"enabled":True,"visible":True},
              {"class":"Button","title":"Cancel","id":1,"enabled":True,"visible":True}]
        self.assertEqual(select_button(rows,"OK")["observed_id"],2)
    def test_hidden(self):
        with self.assertRaises(ValueError):select_button([{"class":"Button","title":"OK","id":1,"visible":False,"enabled":True}],"OK")
    def test_unknown(self):
        with self.assertRaises(ValueError):select_menu([self.row],["File","Export"])

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pid",type=int)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:
        unittest.main(argv=[sys.argv[0]],verbosity=2)
    elif a.pid and a.pid>0:
        print(json.dumps(inventory(a.pid),ensure_ascii=True,indent=2))
    else:p.error("choose --self-test or --pid")
