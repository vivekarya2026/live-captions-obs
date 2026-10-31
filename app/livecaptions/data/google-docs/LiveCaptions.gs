/**
 * Live Captions for Google Docs
 * ==============================
 * Adds a "Live Captions" sidebar to this document. While "Writing" is on, the
 * Live Captions app on your computer sends each sentence here (the original
 * speech + its translation, with the time) and it is added at the end of the doc.
 *
 * One-time setup (about 3 minutes) - see the guide in the Live Captions app
 * (Google Docs section) or docs/GOOGLE_DOCS.md:
 *   1. In your Google Doc: Extensions -> Apps Script. Delete what is there,
 *      paste this whole file, press Save.
 *   2. Deploy -> New deployment -> type "Web app".
 *      Execute as: Me.  Who has access: Anyone.  -> Deploy -> Authorize access.
 *   3. Back in the doc, reload the page. Menu: Live Captions -> Open sidebar.
 *   4. Press "Copy connection link" and paste it into the Live Captions app.
 *
 * "Anyone" only means the app can reach this script without signing in to
 * Google. Nothing can be written without the secret key inside your link.
 */

var PROPS = PropertiesService.getScriptProperties();
var RECENT_MAX = 8;

function onOpen() {
  DocumentApp.getUi().createMenu('Live Captions')
    .addItem('Open sidebar', 'showSidebar')
    .addToUi();
}

function onInstall() { onOpen(); }

function showSidebar() {
  var html = HtmlService.createHtmlOutput(SIDEBAR_HTML).setTitle('Live Captions');
  DocumentApp.getUi().showSidebar(html);
}

// ---------------------------------------------------------------------------
// Called by the sidebar
// ---------------------------------------------------------------------------
function key_() {
  var k = PROPS.getProperty('key');
  if (!k) {
    k = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '').slice(0, 8);
    PROPS.setProperty('key', k);
  }
  return k;
}

function webAppUrl_() {
  var url = '';
  try { url = ScriptApp.getService().getUrl() || ''; } catch (e) {}
  if (!/\/exec$/.test(url)) url = PROPS.getProperty('webAppUrl') || '';
  return url;
}

function getStatus() {
  var doc = DocumentApp.getActiveDocument();
  if (doc && PROPS.getProperty('docId') !== doc.getId()) PROPS.setProperty('docId', doc.getId());
  var url = webAppUrl_();
  var lastSeen = Number(PROPS.getProperty('lastSeen') || 0);
  return {
    writing: PROPS.getProperty('writing') === '1',
    showTime: showTime_(),
    link: url ? url + '?k=' + key_() : '',
    count: Number(PROPS.getProperty('count') || 0),
    appOnline: Date.now() - lastSeen < 20000,
    lastSeen: lastSeen,
    recent: JSON.parse(CacheService.getScriptCache().get('recent') || '[]'),
    docName: doc ? doc.getName() : ''
  };
}

function setWebAppUrl(u) {
  u = String(u || '').trim().replace(/\?.*$/, '');
  if (!/^https:\/\/script\.google\.com\/.+\/exec$/.test(u)) {
    throw new Error('Paste the "Web app" URL from Deploy -> Manage deployments (it ends in /exec).');
  }
  PROPS.setProperty('webAppUrl', u);
  return getStatus();
}

function setWriting(on) {
  PROPS.setProperty('writing', on ? '1' : '0');
  if (on) {
    var body = doc_().getBody();
    var fmt = showTime_() ? 'd MMM yyyy, HH:mm' : 'd MMM yyyy';
    var title = 'Live captions · ' + Utilities.formatDate(new Date(), Session.getScriptTimeZone(), fmt);
    body.appendParagraph(title).setHeading(DocumentApp.ParagraphHeading.HEADING2);
  }
  return getStatus();
}

// Time in front of each line (and in the heading): on unless switched off
function showTime_() { return PROPS.getProperty('showTime') !== '0'; }

function setShowTime(on) {
  PROPS.setProperty('showTime', on ? '1' : '0');
  return getStatus();
}

function newKey() {
  PROPS.deleteProperty('key');  // the old link stops working
  key_();
  return getStatus();
}

// ---------------------------------------------------------------------------
// Called by the Live Captions app (web app)
// ---------------------------------------------------------------------------
function doGet(e) {
  if (!checkKey_(e && e.parameter && e.parameter.k)) return json_({ ok: false, error: 'wrong key: copy the link from the sidebar again' });
  PROPS.setProperty('lastSeen', String(Date.now()));
  return json_(reply_());
}

// The app sends { k, lines: [...], cmd: 'start'|'stop' (optional), showTime: true|false (optional) }
function doPost(e) {
  var data;
  try { data = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false, error: 'bad request' }); }
  if (!checkKey_(data.k)) return json_({ ok: false, error: 'wrong key: copy the link from the sidebar again' });
  PROPS.setProperty('lastSeen', String(Date.now()));
  if (typeof data.showTime === 'boolean') setShowTime(data.showTime);
  if (data.cmd === 'start' && PROPS.getProperty('writing') !== '1') setWriting(true);
  if (data.cmd === 'stop') setWriting(false);
  var writing = PROPS.getProperty('writing') === '1';
  var lines = (data.lines || []).slice(0, 50);
  if (writing && lines.length) {
    var lock = LockService.getScriptLock();
    lock.waitLock(20000);
    try {
      var body = doc_().getBody();
      var time = showTime_();
      for (var i = 0; i < lines.length; i++) appendLine_(body, lines[i], time);
      PROPS.setProperty('count', String(Number(PROPS.getProperty('count') || 0) + lines.length));
      var cache = CacheService.getScriptCache();
      var recent = JSON.parse(cache.get('recent') || '[]').concat(lines).slice(-RECENT_MAX);
      cache.put('recent', JSON.stringify(recent), 21600);
    } finally {
      lock.releaseLock();
    }
  }
  return json_(reply_());
}

function reply_() {
  return { ok: true, writing: PROPS.getProperty('writing') === '1', showTime: showTime_(), doc: docName_() };
}

// One sentence:   10:31:02 · Hindi   आज सत्संग में ...      (small, grey; time only if on)
//                 Today in the satsang ...                  (normal text)
function appendLine_(body, l, time) {
  var src = String(l.src || '').slice(0, 2000);
  var out = String(l.out || '').slice(0, 2000);
  var stamp = time ? String(l.t || '') : '';
  var lang = String(l.lang || '');
  var head = stamp && lang ? stamp + ' · ' + lang : stamp || lang;
  var p1 = body.appendParagraph((head ? head + '   ' : '') + src);
  p1.setHeading(DocumentApp.ParagraphHeading.NORMAL).setSpacingBefore(6).setSpacingAfter(0);
  var t1 = p1.editAsText();
  t1.setFontSize(9).setForegroundColor('#6b6f76').setBold(false).setItalic(false);
  if (head.length) t1.setBold(0, head.length - 1, true);
  var p2 = body.appendParagraph(out || ' ');
  p2.setHeading(DocumentApp.ParagraphHeading.NORMAL).setSpacingBefore(0).setSpacingAfter(4);
  p2.editAsText().setFontSize(11).setForegroundColor('#1f1f1f').setBold(false).setItalic(false);
}

function doc_() {
  var id = PROPS.getProperty('docId');
  return id ? DocumentApp.openById(id) : DocumentApp.getActiveDocument();
}

function docName_() {
  try { return doc_().getName(); } catch (e) { return ''; }
}

function checkKey_(k) {
  var want = PROPS.getProperty('key');
  return !!want && typeof k === 'string' && k === want;
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------
var SIDEBAR_HTML = '<!doctype html><html><head><base target="_top"><meta charset="utf-8">' +
'<style>' +
' body{font:13px Arial,sans-serif;margin:12px;color:#1f1f1f}' +
' h2{font-size:15px;margin:0 0 10px}' +
' .status{padding:8px 10px;border-radius:6px;background:#f1f3f4;margin-bottom:10px;line-height:1.4}' +
' .status b{display:block}' +
' .ok{background:#e6f4ea}.warn{background:#fef7e0}.err{background:#fce8e6}' +
' button{font:inherit;padding:9px 12px;border-radius:6px;border:1px solid #dadce0;background:#fff;cursor:pointer;width:100%;margin-bottom:8px}' +
' button.primary{background:#1a73e8;border-color:#1a73e8;color:#fff;font-weight:bold}' +
' button.stop{background:#c5221f;border-color:#c5221f;color:#fff;font-weight:bold}' +
' button:disabled{opacity:.5;cursor:default}' +
' input{width:100%;box-sizing:border-box;padding:7px;border:1px solid #dadce0;border-radius:6px;font:12px monospace}' +
' .small{font-size:11.5px;color:#5f6368;line-height:1.45;margin:4px 0 10px}' +
' .line{border-top:1px solid #eee;padding:6px 0}.line small{color:#6b6f76;display:block}' +
' details{margin-top:12px}summary{cursor:pointer;color:#5f6368}' +
'</style></head><body>' +
'<h2>Live Captions</h2>' +
'<div id="status" class="status">Loading…</div>' +
'<button id="toggle" class="primary" disabled>Start writing</button>' +
'<label class="small" style="display:flex;gap:6px;align-items:center;cursor:pointer"><input type="checkbox" id="showTime" style="width:auto"> Time stamps (e.g. 10:31:02) in front of each line</label>' +
'<div class="small" id="hint">Each sentence is added at the end of this document: the original speech (small, grey) and the translation under it. ' +
'You can also start, stop and switch time stamps from the Live Captions app; this sidebar can stay closed.</div>' +
'<div id="setup" hidden>' +
'  <b>Connect the app</b>' +
'  <div class="small">Copy this link and paste it in the Live Captions app → <i>Google Docs</i> → <i>Connect</i>.</div>' +
'  <input id="link" readonly onclick="this.select()">' +
'  <button id="copy" style="margin-top:6px">Copy connection link</button>' +
'</div>' +
'<div id="needUrl" hidden>' +
'  <b>One more step</b>' +
'  <div class="small">Paste the <i>Web app URL</i> from <i>Deploy → Manage deployments</i> (ends in /exec):</div>' +
'  <input id="url" placeholder="https://script.google.com/macros/s/…/exec">' +
'  <button id="saveUrl" style="margin-top:6px">Save</button>' +
'</div>' +
'<div id="recentBox" hidden><b>Last lines</b><div id="recent"></div></div>' +
'<details><summary>Security</summary><div class="small">Only the app with your link can write here. ' +
'If you shared the link by mistake, make a new one (the old link stops working):</div>' +
'<button id="newKey">Make a new link</button></details>' +
'<script>' +
'var S=null,busy=false;' +
'function $(i){return document.getElementById(i)}' +
'function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}[c]})}' +
'function render(s){S=s;busy=false;' +
' var st=$("status"),t=$("toggle");' +
' if(!s.link){st.className="status warn";st.innerHTML="<b>Almost ready</b>Finish the setup below.";}' +
' else if(!s.appOnline){st.className="status warn";st.innerHTML="<b>Waiting for the Live Captions app</b>Start the app on your computer and paste the connection link there.";}' +
' else if(s.writing){st.className="status ok";st.innerHTML="<b>● Writing into this document</b>"+s.count+" lines so far";}' +
' else{st.className="status";st.innerHTML="<b>App connected</b>Press Start to write the captions here.";}' +
' t.disabled=!s.link;t.textContent=s.writing?"Stop writing":"Start writing";t.className=s.writing?"stop":"primary";' +
' $("needUrl").hidden=!!s.link;$("setup").hidden=!s.link;$("showTime").checked=s.showTime;' +
' if($("link").value!==s.link)$("link").value=s.link;' +
' var r=s.recent||[];$("recentBox").hidden=!r.length;' +
' $("recent").innerHTML=r.slice().reverse().map(function(l){return "<div class=line><small>"+(s.showTime&&l.t?esc(l.t)+" · ":"")+esc(l.src||"")+"</small>"+esc(l.out||"")+"</div>"}).join("");' +
'}' +
'function fail(e){busy=false;$("status").className="status err";$("status").innerHTML="<b>Problem</b>"+esc(e&&e.message||e);}' +
'function poll(){google.script.run.withSuccessHandler(render).withFailureHandler(fail).getStatus();}' +
'$("toggle").onclick=function(){if(busy||!S)return;busy=true;$("toggle").disabled=true;' +
' google.script.run.withSuccessHandler(render).withFailureHandler(fail).setWriting(!S.writing);};' +
'$("copy").onclick=function(){var i=$("link");i.select();try{navigator.clipboard.writeText(i.value)}catch(e){document.execCommand("copy")}' +
' $("copy").textContent="Copied ✓";setTimeout(function(){$("copy").textContent="Copy connection link"},2000);};' +
'$("showTime").onchange=function(){google.script.run.withSuccessHandler(render).withFailureHandler(fail).setShowTime($("showTime").checked);};' +
'$("saveUrl").onclick=function(){google.script.run.withSuccessHandler(render).withFailureHandler(fail).setWebAppUrl($("url").value);};' +
'$("newKey").onclick=function(){if(confirm("Make a new link? The app must be connected again with the new link."))' +
' google.script.run.withSuccessHandler(render).withFailureHandler(fail).newKey();};' +
'poll();setInterval(poll,2500);' +
'</script></body></html>';
