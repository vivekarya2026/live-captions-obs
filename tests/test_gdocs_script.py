"""Google Docs "script in my doc": the real LiveCaptions.gs (run in Node with fake Google
services) behind a fake script.google.com, driven by livecaptions.gdocs.

    cd app && python3 ../tests/test_gdocs_script.py      (needs node)
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["LIVECAPTIONS_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, str(ROOT / "app"))
from livecaptions import gdocs  # noqa: E402

NODE = shutil.which("node") if subprocess.run(["node", "-v"], capture_output=True).returncode == 0 \
    else "/usr/local/bin/node"

# The script, with fake DocumentApp etc.; reads one request per line on stdin, answers one JSON line.
SIM = r"""
const fs=require('fs'),vm=require('vm'),rl=require('readline').createInterface({input:process.stdin});
const props={},paras=[];let active=true;
const P={getProperty:k=>k in props?props[k]:null,setProperty:(k,v)=>{props[k]=String(v)}};
function para(text){const p={text,h:'NORMAL',bold:[],setHeading(h){p.h=h;return p},setSpacingBefore(){return p},setSpacingAfter(){return p},
 editAsText(){const t={setFontSize(){return t},setForegroundColor(){return t},setItalic(){return t},
 setBold(a,b,c){if(c===true)p.bold.push(p.text.slice(a,b+1));return t}};return t}};paras.push(p);return p}
const doc={getId:()=>'DOC1',getName:()=>'Satsang notes',getUrl:()=>'https://docs.google.com/document/d/DOC1/edit',getBody:()=>({appendParagraph:para})};
const ctx={PropertiesService:{getScriptProperties:()=>P},
 DocumentApp:{getActiveDocument:()=>active?doc:null,openById:id=>{if(id!=='DOC1')throw new Error('Document is missing');return doc},ParagraphHeading:{HEADING2:'H2',NORMAL:'NORMAL'}},
 LockService:{getScriptLock:()=>({waitLock(){},releaseLock(){}})},
 ContentService:{createTextOutput:s=>({s,setMimeType(){return this}}),MimeType:{JSON:'json'}},JSON,String,Number,Date,Math,Error};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);
rl.on('line',l=>{const r=JSON.parse(l);let o;
 if(r.op==='dump')o={paras:paras.map(p=>[p.h,p.text,p.bold])};
 else if(r.op==='detach'){active=false;o={}}
 else if(r.op==='forget'){delete props.docId;o={}}
 else o=JSON.parse((r.op==='post'?ctx.doPost({postData:{contents:r.body}}):ctx.doGet({})).s);
 console.log(JSON.stringify(o))});
"""
sim = subprocess.Popen([NODE, "-e", SIM, str(ROOT / "app/livecaptions/data/google-docs/LiveCaptions.gs")],
                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
lock = threading.Lock()


def script(op, body=""):
    with lock:
        sim.stdin.write(json.dumps({"op": op, "body": body}) + "\n"); sim.stdin.flush()
        return sim.stdout.readline()


class Google(BaseHTTPRequestHandler):  # fake script.google.com, incl. its redirect to the result
    def log_message(self, *a): pass

    def answer(self, code, body, ctype="application/json"):
        self.send_response(code); self.send_header("Content-Type", ctype); self.end_headers(); self.wfile.write(body.encode())

    def route(self, method):
        p = urllib.parse.urlparse(self.path).path
        if p.startswith("/result/"):                       # where Apps Script redirects to
            return self.answer(200, RESULTS.pop(p))
        dep = p.split("/")[3] if p.startswith("/macros/s/") else ""
        if dep == "GOOD":
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode() if method == "POST" else ""
            key = f"/result/{time.time_ns()}"
            RESULTS[key] = script("post" if method == "POST" else "get", body)
            self.send_response(302); self.send_header("Location", key); self.end_headers(); return
        if dep == "PRIVATE":                                # access not "Anyone": Google's sign-in page
            return self.answer(200, "<html><a href='https://accounts.google.com/ServiceLogin'>Sign in</a></html>", "text/html")
        if dep == "OLD":                                    # the 1.0.7/1.0.8 script
            return self.answer(200, json.dumps({"ok": False, "error": "wrong key: copy the link from the sidebar again"}))
        self.answer(404, "<html>Page not found</html>", "text/html")

    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")


RESULTS = {}
srv = ThreadingHTTPServer(("127.0.0.1", 0), Google)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_port}"
real_parse = gdocs.parse_script_url
gdocs.parse_script_url = lambda t: real_parse(t).replace("https://script.google.com", BASE)
gdocs.IDLE_SECONDS = 0.2


def wait(cond, what):
    for _ in range(80):
        if cond():
            return
        time.sleep(0.1)
    raise AssertionError("timed out: " + what)


# --- pasting: every common wrong thing gets a message that says what to do
P = real_parse
assert P("  https://script.google.com/macros/s/AKfycbX12345678901234567890/exec  ") == \
    "https://script.google.com/macros/s/AKfycbX12345678901234567890/exec"
assert P("Web app URL: https://script.google.com/macros/s/AKfycbX12345678901234567890/exec?x=1 copied") == \
    "https://script.google.com/macros/s/AKfycbX12345678901234567890/exec"
assert P("AKfycbX12345678901234567890") == "https://script.google.com/macros/s/AKfycbX12345678901234567890/exec"
assert P("https://script.google.com/a/macros/school.edu/s/AKfycbX12345678901234567890/exec") == \
    "https://script.google.com/a/macros/school.edu/s/AKfycbX12345678901234567890/exec"
for bad, says in [("https://script.google.com/macros/s/AKfycbX123/dev", "test URL"),
                  ("https://script.google.com/home/projects/1abc/edit", "editor link"),
                  ("https://docs.google.com/document/d/1abc/edit", "doc's own link"),
                  ("", "Paste the Web app URL"), ("hello", "Paste the Web app URL")]:
    try:
        P(bad); raise AssertionError("accepted: " + bad)
    except gdocs.GoogleError as e:
        assert says in str(e), (bad, e)

g = gdocs.GoogleDocs()
# --- Connect: the web app's problems, each explained
for dep, says in [("MISSING", "can't find this web app"), ("PRIVATE", "Who has access: Anyone"),
                  ("OLD", "older Live Captions script")]:
    err = g.connect_script(f"https://script.google.com/macros/s/{dep}/exec")
    assert says in err, (dep, err)
    assert not g.linked()

# --- the good case
assert g.connect_script("https://script.google.com/macros/s/GOOD/exec") == ""
st = g.status()
assert st["signed_in"] and st["way"] == "script" and st["doc"] == "Satsang notes", st
assert st["doc_url"].endswith("/DOC1/edit")
g.command(writing=True)
g.add("10:31:02", "Hindi", "आज सत्संग में सेवा 🙏", "Today, sewa in satsang")
wait(lambda: g.sent == 1, "line 1")
g.command(show_time=False)
g.add("10:31:09", "Hindi", "सिमरन करते रहें", "Keep doing simran")
wait(lambda: g.sent == 2, "line 2")
g.command(writing=False)
g.add("10:32:00", "Hindi", "x", "NOT WRITTEN after Stop")
time.sleep(0.5)
g.command(writing=True)                        # Start again: a new heading (time stamps off -> date only)
g.add("10:40:00", "English", "Welcome back", "वापस स्वागत है")
wait(lambda: g.sent == 3, "line 3")

# --- the script can't see its doc (web app call with no active doc): uses the remembered one
script("detach")
g.add("10:41:00", "English", "still here", "अभी भी यहाँ")
wait(lambda: g.sent == 4, "line 4 via remembered doc")
script("forget")
g.add("10:42:00", "English", "lost", "x")
wait(lambda: "Open (or reload) the Google Doc" in g.status()["error"], "explains a lost doc")
assert g.status()["waiting"] == 1, "the line is kept for later"

paras = json.loads(script("dump"))["paras"]
texts = [t for _, t, _ in paras]
print("\n".join(f"  [{h}] {t}" + (f"   bold={b}" if b else "") for h, t, b in paras))
assert paras[0][0] == "H2" and paras[0][1].startswith("Live captions · ") and ":" in paras[0][1]
assert texts[1] == "10:31:02 · Hindi   आज सत्संग में सेवा 🙏" and paras[1][2] == ["10:31:02 · Hindi"]
assert texts[2] == "Today, sewa in satsang"
assert texts[3] == "Hindi   सिमरन करते रहें" and paras[3][2] == ["Hindi"]
assert not any("NOT WRITTEN" in t for t in texts)
assert paras[5][0] == "H2" and ":" not in paras[5][1], "second heading: date only (time stamps off)"
assert texts[6] == "English   Welcome back" and texts[8] == "English   still here"

# --- saved for next start, only this user can read it
saved = json.loads((gdocs.ACCOUNT).read_text())
assert saved["script_url"].endswith("/GOOD/exec") and saved["show_time"] is False
assert os.name == "nt" or (gdocs.ACCOUNT.stat().st_mode & 0o777) == 0o600
g.sign_out()
assert not g.linked() and json.loads(gdocs.ACCOUNT.read_text())["script_url"] == ""
sim.kill()
print("ok: script version, all edge cases")
