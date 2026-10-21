/* Iris editor helpers: Ctrl/Cmd+B/I/E shortcuts and the "/" block menu. */
function irisWrap(v, s, e, m) {
  var sel = v.slice(s, e);
  if (s >= m.length && v.slice(s - m.length, s) === m && v.slice(e, e + m.length) === m)
    return {v: v.slice(0, s - m.length) + sel + v.slice(e + m.length), s: s - m.length, e: e - m.length};
  if (sel.length >= 2 * m.length && sel.slice(0, m.length) === m && sel.slice(-m.length) === m)
    return {v: v.slice(0, s) + sel.slice(m.length, -m.length) + v.slice(e), s: s, e: e - 2 * m.length};
  return {v: v.slice(0, s) + m + sel + m + v.slice(e), s: s + m.length, e: e + m.length};
}
var IRIS_BLOCKS = [
  {k: 'Heading 1', p: '# '}, {k: 'Heading 2', p: '## '}, {k: 'Heading 3', p: '### '},
  {k: 'Bulleted list', p: '- '}, {k: 'Numbered list', p: '1. '}, {k: 'To-do', p: '- [ ] '},
  {k: 'Quote', p: '> '}, {k: 'Divider', p: '---\n'}
];
function irisBlocks(q) {
  q = (q || '').toLowerCase();
  return IRIS_BLOCKS.filter(function (b) { return b.k.toLowerCase().indexOf(q) !== -1; });
}
/* slash trigger: "/" typed at the start of a line (or after only spaces) */
function irisSlashQuery(v, caret) {
  var ls = v.lastIndexOf('\n', caret - 1) + 1, line = v.slice(ls, caret);
  var m = line.match(/^\s*\/([A-Za-z0-9 ]*)$/);
  return m ? {q: m[1], from: ls + line.indexOf('/')} : null;
}
function irisApplyBlock(v, caret, from, block) {
  return {v: v.slice(0, from) + block.p + v.slice(caret), c: from + block.p.length};
}
if (typeof module !== 'undefined') module.exports = {irisWrap: irisWrap, irisBlocks: irisBlocks, irisSlashQuery: irisSlashQuery, irisApplyBlock: irisApplyBlock};
