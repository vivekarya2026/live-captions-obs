/**
 * Live Captions -> this Google Doc
 * ================================
 * Setup (once per doc, about 2 minutes):
 *   1. In this doc: Extensions -> Apps Script. Delete what is there, paste this whole file, press Save.
 *   2. Deploy -> New deployment -> gear -> Web app.  Execute as: Me.  Who has access: Anyone.
 *      -> Deploy -> Authorize access (Google: "unverified app" -> Advanced -> Go to ... -> Allow).
 *   3. Copy the "Web app URL" (ends in /exec) and paste it in the Live Captions app
 *      (Google Docs -> Use a script in my doc -> Connect).
 *
 * Start/Stop and time stamps are in the Live Captions app. Each sentence is added at the
 * end of this doc. Treat the Web app URL like a password: whoever has it can add text here.
 */

var VERSION = 2;

function onOpen() { remember_(); }

function doGet() { return run_(function (doc) { return {}; }); }

function doPost(e) {
  return run_(function (doc) {
    var d = JSON.parse(e.postData.contents);
    var body = doc.getBody();
    var time = d.showTime !== false;
    if (d.heading) {
      body.appendParagraph(String(d.heading).slice(0, 200)).setHeading(DocumentApp.ParagraphHeading.HEADING2);
    }
    var lines = (d.lines || []).slice(0, 50);
    for (var i = 0; i < lines.length; i++) line_(body, lines[i], time);
    return { added: lines.length };
  });
}

// One sentence:   10:31:02 · Hindi   आज सत्संग में ...      (small, grey; time only if on)
//                 Today in the satsang ...                  (normal text)
function line_(body, l, time) {
  var src = String(l.src || '').slice(0, 2000);
  var out = String(l.out || '').slice(0, 2000);
  var stamp = time ? String(l.t || '') : '';
  var lang = String(l.lang || '');
  var head = stamp && lang ? stamp + ' · ' + lang : stamp || lang;
  var p1 = body.appendParagraph((head ? head + '   ' : '') + src);
  p1.setHeading(DocumentApp.ParagraphHeading.NORMAL).setSpacingBefore(6).setSpacingAfter(0);
  var t1 = p1.editAsText();
  t1.setFontSize(9).setForegroundColor('#6b6f76').setBold(false).setItalic(false);
  if (head) t1.setBold(0, head.length - 1, true);
  var p2 = body.appendParagraph(out || ' ');
  p2.setHeading(DocumentApp.ParagraphHeading.NORMAL).setSpacingBefore(0).setSpacingAfter(4);
  p2.editAsText().setFontSize(11).setForegroundColor('#1f1f1f').setBold(false).setItalic(false);
}

function run_(work) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);
    var doc = doc_();
    var r = work(doc);
    r.ok = true; r.v = VERSION; r.doc = doc.getName(); r.url = doc.getUrl();
    return out_(r);
  } catch (err) {
    return out_({ ok: false, v: VERSION, error: String(err && err.message || err) });
  } finally {
    try { lock.releaseLock(); } catch (e) {}
  }
}

// The doc this script belongs to (remembered when the doc is opened)
function doc_() {
  var doc = null;
  try { doc = DocumentApp.getActiveDocument(); } catch (e) {}
  if (doc) { remember_(doc); return doc; }
  var id = PropertiesService.getScriptProperties().getProperty('docId');
  if (!id) throw new Error('Open (or reload) the Google Doc once, then press Connect again.');
  return DocumentApp.openById(id);
}

function remember_(doc) {
  try {
    doc = doc || DocumentApp.getActiveDocument();
    if (doc) PropertiesService.getScriptProperties().setProperty('docId', doc.getId());
  } catch (e) {}
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
