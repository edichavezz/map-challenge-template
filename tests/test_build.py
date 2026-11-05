import re

import build

TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


def make_day(days, folder, files):
    path = days / folder
    path.mkdir(parents=True)
    for name, content in files.items():
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(path / name, mode) as f:
            f.write(content)


def build_fixture(tmp_path):
    days = tmp_path / "days"
    make_day(days, "01-points", {
        "map.html": "<html>a map</html>",
        "notes.md": "# Where the bakeries are\n\nI wanted to see **why**.",
        "sources.toml": (
            '[[source]]\nname = "Bakeries"\nurl = "https://example.org/bakeries"\n'
            'from = "City open data"\nwhat = "One row per bakery"\ntime = "2026"\n'
            'resolution = ""\nlicence = "CC BY 4.0"\n'
        ),
        "map.py": 'import folium\nimport pandas as pd\nimport os\nfrom mapkit import palette\nTOKEN = "pk.abcdefghijklmnopqrstuvwxyz0123456789"\n',
    })
    make_day(days, "02-lines", {"notes.md": "# Still working on it\n"})   # no map yet
    make_day(days, "03-polygons", {"map.png": TINY_PNG, "notes.md": "# A photo\n"})
    out = tmp_path / "site"
    built = build.build(out_dir=out, days_dir=days)
    return out, built


def test_calendar_has_all_30_days(tmp_path):
    out, _ = build_fixture(tmp_path)
    index = (out / "index.html").read_text()
    assert index.count('class="tile done"') == 2
    assert index.count('class="tile empty"') == 28
    assert "of 30 maps" not in index           # no progress count under the intro


def test_only_finished_days_get_pages(tmp_path):
    out, _ = build_fixture(tmp_path)
    assert (out / "days/01/index.html").exists()
    assert not (out / "days/02").exists()
    assert (out / "days/03/index.html").exists()


def test_day_page_shows_notes_sources_and_missing_fields(tmp_path):
    out, built = build_fixture(tmp_path)
    page = (out / "days/01/index.html").read_text()
    assert "Where the bakeries are" in page
    assert "<strong>why</strong>" in page
    assert 'href="https://example.org/bakeries"' in page
    assert 'missing: add "resolution"' in page
    assert page.count("⚠ missing") == 1
    day1 = built[0]
    assert any("'resolution' is empty" in w for w in day1.warnings)


def test_tools_and_token_hiding(tmp_path):
    out, built = build_fixture(tmp_path)
    page = (out / "days/01/index.html").read_text()
    assert built[0].tools == ["Python", "folium", "pandas"]
    assert "pk.abcdefghijklmnopqrstuvwxyz" not in page
    assert "[TOKEN REMOVED]" in page


def test_image_maps_use_img_and_are_their_own_preview(tmp_path):
    out, _ = build_fixture(tmp_path)
    page = (out / "days/03/index.html").read_text()
    assert '<img src="map.png"' in page
    assert 'src="days/03/map.png"' in (out / "index.html").read_text()


def test_links_are_relative_so_site_works_anywhere(tmp_path):
    out, _ = build_fixture(tmp_path)
    for html in out.rglob("*.html"):
        text = html.read_text()
        assert not re.search(r'(href|src)="/(?!/)', text), html


def test_previews_are_remade_when_the_map_changes(tmp_path, monkeypatch):
    import os
    calls = []

    def fake_thumbnail(map_html, png):
        calls.append(map_html)
        png.write_bytes(TINY_PNG)
        return True

    monkeypatch.setattr(build, "make_thumbnail", fake_thumbnail)
    days = tmp_path / "days"
    make_day(days, "01-points", {"map.html": "<html>v1</html>", "notes.md": "# T\n"})
    out = tmp_path / "site"
    build.build(out_dir=out, days_dir=days, make_thumbs=True)
    build.build(out_dir=out, days_dir=days, make_thumbs=True)
    assert len(calls) == 1                       # unchanged map: preview kept
    map_file = days / "01-points" / "map.html"
    later = (days / "01-points" / "thumb.png").stat().st_mtime + 10
    os.utime(map_file, (later, later))           # the map gets edited
    build.build(out_dir=out, days_dir=days, make_thumbs=True)
    assert len(calls) == 2                       # preview remade


def test_made_by_link_on_every_page(tmp_path):
    out, _ = build_fixture(tmp_path)
    url = build.load_toml(build.ROOT / "site.toml").get("made_by_url")
    if url:
        assert (out / "index.html").read_text().count(f'href="{url}"') >= 2   # byline + footer (+ any footer links)
        assert f'href="{url}"' in (out / "days/01/index.html").read_text()


def footer_site(tmp_path, **changes):
    """Build a one-day site with some site.toml settings changed. Returns (index, day page)."""
    settings = {**build.load_toml(build.ROOT / "site.toml"), **changes}
    for key in [k for k, v in changes.items() if v is None]:
        settings.pop(key)
    days = tmp_path / "days"
    make_day(days, "01-points", {"map.html": "<html>a map</html>", "notes.md": "# T\n"})
    out = tmp_path / "site"
    build.build(out_dir=out, days_dir=days, settings=settings)
    return (out / "index.html").read_text(), (out / "days/01/index.html").read_text()


def test_original_site_invites_visitors_to_use_the_template(tmp_path):
    index, day = footer_site(tmp_path, template=None, template_repo="https://github.com/me/tpl")
    invite = "Use this template for your own"
    for page in (index, day):
        assert page.count(invite) == 1
        assert 'href="https://github.com/me/tpl"' in page
        assert "Template by" not in page
        assert invite not in page[page.index("<footer"):]           # not in the footer
    byline = index[index.index('class="byline"'):index.index('class="calendar"')]
    assert invite in byline                                         # under the intro
    how = day[day.index('class="how"'):day.index('class="pnext"')]
    assert invite in how                                            # in "How it was made"


def test_copies_credit_the_template_author(tmp_path):
    credit = {"by": "Ada Lovelace", "url": "https://ada.example/", "repo": "https://github.com/ada/tpl"}
    pages = footer_site(tmp_path, template=credit, template_repo=None)
    for page in pages:
        assert "Template by" in page and "Ada Lovelace" in page
        assert 'href="https://ada.example/"' in page
        assert 'href="https://github.com/ada/tpl"' in page
        assert "Use this template for your own" not in page


def test_no_template_line_when_neither_is_set(tmp_path):
    for page in footer_site(tmp_path, template=None, template_repo=None):
        assert "template-note" not in page and "template-invite" not in page


def test_made_with_follows_the_name(tmp_path):
    index, _ = footer_site(tmp_path, name="Ada", made_by_url="https://ada.example/",
                           made_with="with a little help from Claude")
    assert '>Ada</a> with a little help from Claude' in index


def test_prev_next_skip_unfinished_days(tmp_path):
    out, _ = build_fixture(tmp_path)
    page = (out / "days/01/index.html").read_text()
    assert 'href="../03/index.html"' in page
    assert "../02/" not in page


def test_map_arrows_go_to_neighbouring_finished_days(tmp_path):
    out, _ = build_fixture(tmp_path)

    def arrow(page, rel):
        match = re.search(rf'<a class="maparrow {rel}" rel="{rel}" href="([^"]+)"', page)
        return match and match.group(1)

    first = (out / "days/01/index.html").read_text()
    last = (out / "days/03/index.html").read_text()
    assert arrow(first, "next") == "../03/index.html"      # skips unfinished day 02
    assert 'rel="prev"' not in first                         # nothing before day 01
    assert arrow(last, "prev") == "../01/index.html"
    assert 'rel="next"' not in last                          # nothing after day 03


def test_tag_from_day_toml_shows_on_calendar_and_day_page(tmp_path):
    days = tmp_path / "days"
    make_day(days, "01-points", {"map.html": "<html>a map</html>", "notes.md": "# One\n",
                                 "day.toml": 'tag = "Hand-coded"\n'})
    make_day(days, "02-lines", {"map.html": "<html>a map</html>", "notes.md": "# Two\n"})   # no day.toml
    make_day(days, "03-polygons", {"map.html": "<html>a map</html>", "notes.md": "# Three\n",
                                   "day.toml": 'tag = "AI-coded'})                        # typo: no closing quote
    out = tmp_path / "site"
    built = build.build(out_dir=out, days_dir=days)
    index = (out / "index.html").read_text()
    assert index.count('class="tag"') == 1
    assert '<span class="tag">Hand-coded</span>' in index
    assert '<span class="tag">Hand-coded</span>' in (out / "days/01/index.html").read_text()
    assert 'class="tag"' not in (out / "days/02/index.html").read_text()
    assert built[0].tag == "Hand-coded" and built[1].tag == ""
    assert any("day.toml has a typo" in w for w in built[2].warnings)


def test_extra_pictures_from_day_toml_go_under_the_map(tmp_path):
    days = tmp_path / "days"
    make_day(days, "01-points", {
        "map.html": "<html>a map</html>", "notes.md": "# One\n", "lifted.png": TINY_PNG,
        "day.toml": ('tag = "AI-coded"\n\n[[extra]]\nfile = "lifted.png"\ncaption = "Every lake, side by side"\n\n'
                     '[[extra]]\nfile = "missing.png"\ncaption = "Not made yet"\n\n'
                     '[[extra]]\nfile = "../02-lines/notes.md"\n'),
    })
    out = tmp_path / "site"
    built = build.build(out_dir=out, days_dir=days)
    page = (out / "days/01/index.html").read_text()
    assert '<img src="lifted.png" alt="Every lake, side by side"' in page
    assert "<figcaption>Every lake, side by side</figcaption>" in page
    assert (out / "days/01/lifted.png").read_bytes() == TINY_PNG
    assert page.count('<figure class="extra">') == 1               # only the picture that exists
    assert 'src="missing.png"' not in page and 'src="../02-lines' not in page
    assert any("missing.png" in w for w in built[0].warnings)
    assert any("../02-lines/notes.md" in w for w in built[0].warnings)


def test_extra_html_pages_go_in_a_frame(tmp_path):
    days = tmp_path / "days"
    make_day(days, "01-points", {
        "map.html": "<html>a map</html>", "notes.md": "# One\n", "lifted.html": "<html>zoom me</html>",
        "day.toml": '[[extra]]\nfile = "lifted.html"\ncaption = "Zoom in"\n'})
    out = tmp_path / "site"
    build.build(out_dir=out, days_dir=days)
    page = (out / "days/01/index.html").read_text()
    assert '<iframe src="lifted.html" title="Zoom in" loading="lazy"' in page
    assert (out / "days/01/lifted.html").read_text() == "<html>zoom me</html>"


def test_local_server_tells_the_browser_not_to_cache(tmp_path):
    import functools, http.server, threading, urllib.request
    (tmp_path / "index.html").write_text("hi")
    handler = functools.partial(build.NoCacheHandler, directory=str(tmp_path))
    handler.log_message = lambda *a, **k: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/index.html") as r:
            assert r.headers["Cache-Control"] == "no-store"
            assert r.read() == b"hi"
    finally:
        server.shutdown()


def test_downloads_from_day_toml_become_buttons(tmp_path):
    days = tmp_path / "days"
    make_day(days, "01-points", {
        "map.html": "<html>a map</html>", "notes.md": "# One\n", "lifted.png": TINY_PNG,
        "day.toml": ('[[download]]\nfile = "lifted.png"\nlabel = "Download the picture"\n\n'
                     '[[download]]\nfile = "nope.png"\n')})
    out = tmp_path / "site"
    built = build.build(out_dir=out, days_dir=days)
    page = (out / "days/01/index.html").read_text()
    assert '<a class="download" href="lifted.png" download>' in page
    assert "Download the picture" in page
    assert '<img src="lifted.png"' not in page                     # a download, not shown on the page
    assert (out / "days/01/lifted.png").read_bytes() == TINY_PNG
    assert 'href="nope.png"' not in page
    assert any("nope.png" in w for w in built[0].warnings)
