from iris.webui import render_notes_md as R, inline_md as I

def test_inline_formats_and_escapes():
    assert I("a **b** and *c* and `d` ~~e~~") == "a <strong>b</strong> and <em>c</em> and <code>d</code> <del>e</del>"
    assert I("<script>**x**</script>") == "&lt;script&gt;<strong>x</strong>&lt;/script&gt;"
    assert I("2 * 3 * 4") == "2 * 3 * 4"            # spaced stars are not italics

def test_title_skipped_only_for_generated_notes():
    assert "<h2" not in R("# Meeting\nbody", skip_title=True)
    assert "<h2 class=big>Roadmap</h2>" in R("# Roadmap\nbody", skip_title=False)

def test_later_h1_still_renders_for_generated_notes():
    assert "<h2 class=big>Later</h2>" in R("# Title\n# Later")

def test_blocks():
    h = R("- [x] done\n- [ ] todo\n  - nested\n1. one\n> quote\n---")
    assert 'class="todo done"' in h and 'class=todo>' in h
    assert "margin-left:20px" in h and "<span class=n>1.</span>" in h
    assert "<blockquote>quote</blockquote>" in h and "<hr" in h

def test_timestamp_quote_still_works():
    assert 'class=ts>00:05' in R('  > "keep it local" [00:05]')
