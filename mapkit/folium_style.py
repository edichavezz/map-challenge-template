"""
folium_style.py — make folium maps match the website.

    import folium
    from mapkit import palette as P
    from mapkit.folium_style import add_basemap, style_map, add_legend, add_title

    m = folium.Map(location=[41.88, -87.63], zoom_start=12, tiles=None)
    add_basemap(m, "light")                        # the background map
    style_map(m)                                   # site font, ink buttons, paper tooltips
    add_title(m, "Where the bakeries are")         # optional title box, top-left
    cafe, bakery = P.categorical(2)
    add_legend(m, "Type of shop", {"Café": cafe, "Bakery": bakery})
    add_credit(m, OSM_DATA_CREDIT)                 # credit YOUR data, bottom-right corner
    m.save("map.html")

These only change how the map LOOKS. Everything about your data — what goes on
the map, colours, tooltips — is still your folium code.
"""

import os
from html import escape

import folium
from branca.element import MacroElement
from jinja2 import Template

from mapkit import palette as P

_FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:'
    'opsz,wght@12..96,400;12..96,600;12..96,800&display=swap" rel="stylesheet">'
)

_CSS = f"""
<style>
  .leaflet-container {{ font-family: "Bricolage Grotesque", system-ui, sans-serif; background: {P.WATER}; }}
  .leaflet-bar {{ border: 1.5px solid {P.INK} !important; border-radius: 0 !important; box-shadow: none !important; }}
  .leaflet-bar a {{ background: {P.PAPER}; color: {P.INK}; border-radius: 0 !important; border-bottom-color: {P.INK} !important; }}
  .leaflet-bar a:hover {{ background: {P.HIGHLIGHT}; }}
  .leaflet-tooltip, .leaflet-popup-content-wrapper {{
    background: {P.PAPER}; color: {P.INK}; border: 1.5px solid {P.INK};
    border-radius: 0; box-shadow: 3px 3px 0 {P.INK}; font-size: 13px;
  }}
  .leaflet-popup-tip {{ background: {P.INK}; }}
  .leaflet-tooltip-top:before {{ border-top-color: {P.INK}; }}
  .leaflet-control-attribution {{ background: rgba(241, 236, 226, .85) !important; color: {P.MUTED}; font-size: 10px; }}
  .mk-box {{
    position: fixed; z-index: 1000; background: {P.PAPER}; color: {P.INK};
    border: 1.5px solid {P.INK}; padding: 10px 12px; font-family: "Bricolage Grotesque", system-ui, sans-serif;
  }}
  .mk-legend {{ right: 12px; bottom: 28px; font-size: 13px; line-height: 1.7; max-width: 260px; }}
  .mk-legend b {{ display: block; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }}
  .mk-legend i {{ display: inline-block; width: 13px; height: 13px; margin-right: 7px; vertical-align: -2px; border: 1.5px solid {P.INK}; }}
  .mk-legend i.circle {{ border-radius: 50%; }}
  .mk-legend i.line {{ height: 4px; width: 22px; border: 0; vertical-align: 3px; }}
  .mk-title {{ left: 56px; top: 12px; max-width: 360px; }}
  .mk-title h1 {{ margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.1; }}
  .mk-title p {{ margin: 4px 0 0; font-size: 13px; color: {P.MUTED}; }}
</style>
"""


# Background maps ("tiles"). A tile URL has {z}/{x}/{y} slots that Leaflet fills in
# as you pan and zoom. If one of these ever stops working, change it here only.
#
# The Esri ones need no account. Their sharp detail stops at zoom 16 (a few streets);
# closer than that the tiles are stretched. For crisp street-level maps use Mapbox.
_ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/{layer}/MapServer/tile/{{z}}/{{y}}/{{x}}"
_ESRI_CREDIT = ("Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors, "
                "and the GIS User Community")
_OSM_CREDIT = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
_MAPBOX_CREDIT = ('&copy; <a href="https://www.mapbox.com/about/maps/">Mapbox</a> ' + _OSM_CREDIT)

BASEMAPS = {
    # name:            (tile URL, labels drawn on top (or None), credit, sharpest zoom)
    "light":          (_ESRI.format(layer="World_Light_Gray_Base"), _ESRI.format(layer="World_Light_Gray_Reference"), _ESRI_CREDIT, 16),
    "light-nolabels": (_ESRI.format(layer="World_Light_Gray_Base"), None, _ESRI_CREDIT, 16),
    "dark":           (_ESRI.format(layer="World_Dark_Gray_Base"), _ESRI.format(layer="World_Dark_Gray_Reference"), _ESRI_CREDIT, 16),
    "osm":            ("https://tile.openstreetmap.org/{z}/{x}/{y}.png", None, _OSM_CREDIT, 19),
}


def add_basemap(m, style="light", mapbox_style="mapbox/light-v11"):
    """Add a background map.

    style: "light" (default), "light-nolabels", "dark", "osm", or "mapbox".

    "mapbox" needs a free Mapbox token in the MAPBOX_TOKEN environment variable
    (never paste it into your code; see README). mapbox_style can be any style
    id, including your own from Mapbox Studio, e.g. "yourname/abc123".
    """
    if style == "mapbox":
        token = os.environ.get("MAPBOX_TOKEN")
        if not token:
            raise RuntimeError("No MAPBOX_TOKEN found. See the README section 'Using Mapbox'.")
        url = f"https://api.mapbox.com/styles/v1/{mapbox_style}/tiles/256/{{z}}/{{x}}/{{y}}@2x?access_token={token}"
        # control=False: the basemap never gets an on/off switch in folium.LayerControl
        folium.TileLayer(tiles=url, attr=_MAPBOX_CREDIT, name="Mapbox", max_zoom=20, control=False).add_to(m)
        return m
    if style not in BASEMAPS:
        raise ValueError(f"Unknown basemap {style!r}. Choose from: {', '.join(BASEMAPS)}, mapbox")
    base, labels, credit, sharpest = BASEMAPS[style]
    folium.TileLayer(tiles=base, attr=credit, name=style, max_native_zoom=sharpest, max_zoom=19,
                     control=False).add_to(m)
    if labels:
        folium.TileLayer(tiles=labels, attr=credit, name=f"{style} labels", overlay=True,
                         control=False, max_native_zoom=sharpest, max_zoom=19).add_to(m)
    return m


def style_map(m):
    """Site font, ink-outlined zoom buttons, paper-coloured tooltips and popups."""
    m.get_root().header.add_child(folium.Element(_FONT_LINK + _CSS))
    return m


def add_legend(m, title, items, shape="circle"):
    """A legend box in the bottom-right corner.

    items: {"label": "#hexcolour", ...}   shape: "circle", "square" or "line"
    """
    rows = "".join(
        f'<div><i class="{shape}" style="background:{colour}"></i>{escape(str(label))}</div>'
        for label, colour in items.items()
    )
    html = f'<div class="mk-box mk-legend"><b>{escape(title)}</b>{rows}</div>'
    m.get_root().html.add_child(folium.Element(html))
    return m


OSM_DATA_CREDIT = ('Data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
                   'contributors')


class _Credit(MacroElement):
    _template = Template("""
        {% macro script(this, kwargs) %}
            {{ this._parent.get_name() }}.attributionControl.addAttribution({{ this.html|tojson }});
        {% endmacro %}
    """)

    def __init__(self, html):
        super().__init__()
        self._name = "Credit"
        self.html = html


def add_credit(m, html):
    """Credit your DATA in the map's bottom-right corner, next to the basemap's credit.

    The basemap credits itself, but the data you draw on top needs its own credit
    (most licences ask for it on the map, not just on the day page). html can
    include a link, e.g. OSM_DATA_CREDIT for anything from OpenStreetMap.
    """
    _Credit(html).add_to(m)
    return m


class _ConnectToExtras(MacroElement):
    _template = Template("""
        {% macro script(this, kwargs) %}
        (function () {
            const map = {{ this._parent.get_name() }};
            const INK = {{ this.ink|tojson }};
            const onDayPage = window.parent !== window;
            const idOf = (p) => p && (p.osm_id || p.lake_osm_id);   // a lake, or the lake a swim spot is on
            let marks = [];

            // outline a shape (or ring a point) in ink, with its name above; optionally fly there
            function mark(layer, latlng, name, fly) {
                marks.forEach((l) => l.remove());
                marks = [];
                const style = {color: INK, weight: 3, fill: false, interactive: false};
                let where;
                if (layer && layer.getBounds) {
                    marks.push(L.geoJSON(layer.feature, {style: style, interactive: false}).addTo(map));
                    where = layer.getBounds().getCenter();
                    if (fly) map.flyToBounds(layer.getBounds(), {maxZoom: 14, padding: [60, 60]});
                } else {
                    where = latlng || layer.getLatLng();
                    marks.push(L.circleMarker(where, Object.assign({radius: 16}, style)).addTo(map));
                    if (fly) map.flyTo(where, 13);
                }
                if (name) marks.push(L.tooltip({permanent: true, direction: "top", offset: [0, -14]})
                                      .setLatLng(where).setContent(name).addTo(map));
            }

            // tell the extras under the map (via static/site.js) which lake was picked here
            function tell(layer) {
                const p = layer.feature.properties;
                if (onDayPage && idOf(p)) window.parent.postMessage({type: "mk-select", osm_id: String(idOf(p)), name: p.name}, "*");
            }

            // 1. an extra asks: show this lake
            window.addEventListener("message", (e) => {
                const msg = e.data;
                if (!msg || msg.type !== "mk-highlight") return;
                let found = null;
                if (msg.osm_id) map.eachLayer((l) => {
                    const p = l.feature && l.feature.properties;
                    if (!found && p && String(p.osm_id) === String(msg.osm_id) && l.getBounds) found = l;
                });
                mark(found, L.latLng(msg.lat, msg.lon), msg.name, true);
            });

            // 2. a click on a lake (or a swim spot on one) here: outline it and tell the extras
            map.eachLayer((l) => {
                const p = l.feature && l.feature.properties;
                if (idOf(p)) l.on("click", () => { mark(l, null, p.name, false); tell(l); });
            });

            {% if this.search %}
            // 3. a search box: every named shape, by "name · what it is"
            const places = new Map();
            map.eachLayer((l) => {
                const p = l.feature && l.feature.properties;
                if (!p || !p.name || p.name.startsWith("Unnamed")) return;
                const label = p.kind ? `${p.name} · ${p.kind}${p.nation ? " · " + p.nation : ""}` : `${p.name} · swim spot`;
                if (!places.has(label)) places.set(label, l);
            });
            const box = L.DomUtil.create("div", "mk-box mk-mapsearch", map.getContainer());
            box.innerHTML = '<input list="mk-places" aria-label="Search">' + '<datalist id="mk-places"></datalist>';
            const input = box.querySelector("input");
            input.placeholder = {{ this.search|tojson }};
            L.DomEvent.disableClickPropagation(box);
            L.DomEvent.disableScrollPropagation(box);
            input.addEventListener("focus", () => {
                const list = box.querySelector("datalist");
                if (list.children.length) return;
                [...places.keys()].sort().forEach((label) => {
                    const option = document.createElement("option");
                    option.value = label;
                    list.append(option);
                });
            });
            input.addEventListener("change", () => {
                const layer = places.get(input.value);
                if (!layer) return;
                mark(layer, null, layer.feature.properties.name, true);
                tell(layer);
                input.value = "";
                input.blur();
            });
            const css = document.createElement("style");
            css.textContent = ".mk-mapsearch { position: absolute; left: 12px; bottom: 30px; padding: 5px 6px; }" +
                " .mk-mapsearch input { width: 280px; font: inherit; font-size: 14px; border: 0; outline: 0;" +
                " background: transparent; color: " + INK + "; }" +
                " @media (max-width: 640px) { .mk-mapsearch { right: 12px; } .mk-mapsearch input { width: 100%; }" +
                " .mk-legend { bottom: 76px; } }";   // phones: lift the legend above the search box
            document.head.append(css);
            {% endif %}
        })();
        {% endmacro %}
    """)

    def __init__(self, search):
        super().__init__()
        self._name = "ConnectToExtras"
        self.ink = P.INK
        self.search = search


def connect_to_extras(m, search=None):
    """Connect this map with interactive extras under it on the day page (e.g. Day 3's lifted lakes).

    - An extra can ask the map to show a place: it sends {type: "mk-highlight", osm_id, lat, lon, name},
      and the map flies there and outlines the shape with that osm_id (or rings the point).
    - Clicking a shape with an osm_id (or a lake_osm_id, for things on a lake) outlines it and sends
      {type: "mk-select", osm_id, name}, so the extras can pick the same lake.
    - search="Find a lake…" adds a search box (bottom left) for every named shape on the map.

    static/site.js passes the messages between the frames on the day page.
    """
    _ConnectToExtras(search).add_to(m)
    return m


def add_title(m, title, subtitle=""):
    """A title box in the top-left corner (next to the zoom buttons)."""
    sub = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    html = f'<div class="mk-box mk-title"><h1>{escape(title)}</h1>{sub}</div>'
    m.get_root().html.add_child(folium.Element(html))
    return m
