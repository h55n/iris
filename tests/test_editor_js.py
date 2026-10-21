"""The editor helpers are plain JS; run them under node."""
import json, os, subprocess
JS = os.path.join(os.path.dirname(__file__), "..", "iris", "static_editor.js")

def run(expr):
    code = f"const m=require({json.dumps(os.path.abspath(JS))});console.log(JSON.stringify({expr}))"
    return json.loads(subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout)

def test_bold_wraps_selection():
    assert run("m.irisWrap('hello world',0,5,'**')") == {"v": "**hello** world", "s": 2, "e": 7}

def test_bold_toggles_off_when_selection_is_inside_markers():
    assert run("m.irisWrap('**hello** world',2,7,'**')") == {"v": "hello world", "s": 0, "e": 5}

def test_bold_toggles_off_when_markers_are_selected():
    assert run("m.irisWrap('**hello** x',0,9,'**')") == {"v": "hello x", "s": 0, "e": 5}

def test_empty_selection_puts_caret_between_markers():
    r = run("m.irisWrap('ab',1,1,'*')")
    assert r == {"v": "a**b", "s": 2, "e": 2}

def test_slash_query_only_at_line_start():
    assert run("m.irisSlashQuery('text\\n/hea',9)") == {"q": "hea", "from": 5}
    assert run("m.irisSlashQuery('a/b',3)") is None
    assert run("m.irisSlashQuery('  /',3)") == {"q": "", "from": 2}

def test_block_filter_and_apply():
    assert [b["k"] for b in run("m.irisBlocks('head')")] == ["Heading 1", "Heading 2", "Heading 3"]
    assert run("m.irisBlocks('zzz')") == []
    assert run("m.irisApplyBlock('x\\n/to',5,2,m.irisBlocks('to-do')[0])") == {"v": "x\n- [ ] ", "c": 8}
