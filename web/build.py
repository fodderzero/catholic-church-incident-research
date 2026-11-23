from collections import Counter
from datetime import date
from html import escape
from pathlib import Path
import json, re, unicodedata

import os
import sqlite3
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ.get("ATLAS_OUTPUT", "public-atlas"))
DB = ROOT.parent / "Catholic_Church_Incident_Research.sqlite"
ORIGIN = "https://catholic-incident-atlas.toasty-wolf-9016.chatgpt.site"
REPO = "https://github.com/fodderzero/catholic-church-incident-research"
links = json.loads((ROOT / "links.json").read_text())
connection = sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)
connection.row_factory = sqlite3.Row
if connection.execute("pragma integrity_check").fetchone()[0] != "ok" or connection.execute("pragma foreign_key_check").fetchall():
    raise ValueError("Database integrity check failed")
CASES = [dict(row) for row in connection.execute("SELECT * FROM case_search WHERE review_status='reviewed'")]
expected = connection.execute("SELECT count(*) FROM incidents WHERE review_status='reviewed'").fetchone()[0]
if len({c["incident_id"] for c in CASES}) != expected or len(CASES) != expected:
    raise ValueError("Reviewed incident count differs from case_search")
# An optional public headline can be maintained with the rest of the case in SQLite.
headlines = {}
if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='public_headlines'").fetchone():
    headlines = dict(connection.execute("SELECT incident_id, headline FROM public_headlines"))
for c in CASES:
    c["sources"] = [dict(row) for row in connection.execute("SELECT * FROM sources WHERE incident_id=? ORDER BY source_id", (c["incident_id"],))]
    if not c["sources"] or not c["atlas_date"]:
        raise ValueError(f"Case {c['incident_id']} lacks a source or counting date")
    for source in c["sources"]:
        url = urlsplit(source["url"])
        if url.scheme not in ("http","https") or not url.netloc:
            raise ValueError(f"Invalid source URL for case {c['incident_id']}")
dates = [s["accessed_on"] for c in CASES for s in c["sources"]] + [c["assessed_on"] for c in CASES]
CUTOFF = date.fromisoformat(max(filter(None, dates), default=date.today().isoformat())).strftime("%B %d, %Y").replace(" 0", " ")
def e(value): return escape(str(value or ""), quote=True)
def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()).strip('-')
def pretty(value,fmt='%b %d, %Y'):
    return date.fromisoformat(value).strftime(fmt).replace(' 0',' ')
def monthname(value): return pretty(value+'-01','%B %Y')
def monthurl(value): return '/months/'+value+'/'
def save(path, html):
    target=OUT / path.strip('/') / 'index.html'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(html)
def icon(name):
    paths={"pin":'<path d="M12 21s7-7.2 7-13A7 7 0 0 0 5 8c0 5.8 7 13 7 13Z"/><circle cx="12" cy="8" r="2.3"/>',
    "book":'<path d="M3 5c4-1 6 0 9 2 3-2 5-3 9-2v14c-4-1-6 0-9 2-3-2-5-3-9-2zM12 7v14"/>',
    "map":'<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15M15 6v15"/>',
    "copy":'<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 5V3H3v13h2"/>',
    "calendar":'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v5m10-5v5M3 11h18"/>',
    "locate":'<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 1v5m0 12v5M1 12h5m12 0h5"/>',
    "search":'<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
    "globe":'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    "chev":'<path d="m7 10 5 5 5-5"/>',
    "link":'<path d="m9 15 6-6m-5-1 3-3a4 4 0 0 1 6 6l-3 3m-2 2-3 3a4 4 0 0 1-6-6l3-3"/>'}
    return '<svg class="icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">'+paths[name]+'</svg>'
for c in CASES:
    record_id = str(c['incident_id'])
    c['place'] = {'Near Fraserwood, Rural Municipality of Armstrong':'Near Fraserwood','Khari Bamuner Chak (Bamunerchak)':'Khari Bamuner Chak','Malaguna 3, Rabaul area':'Malaguna 3'}.get(c['locality'],c['locality']) or c['region'] or c['country']
    metadata = links.get(record_id, {})
    c['title'] = headlines.get(c['incident_id']) or metadata.get('headline') or f"{c['event_type'].capitalize()} in {c['place']}"
    c['key'] = metadata.get('slug', record_id)
    c['url']='/cases/'+c['key']+'/'
    c['month']=c['atlas_date'][:7]
assert len({c['key'] for c in CASES})==len(CASES)
CASES.sort(key=lambda c:(c['atlas_date'],c['place']),reverse=True)
previous = Path(os.environ.get("ATLAS_PREVIOUS_INDEX", "previous-publication.json"))
prior = json.loads(previous.read_text()) if previous.is_file() else {}
active_months = sorted({c['month'] for c in CASES}, reverse=True)
months = sorted(set(active_months) | set(prior.get('months', [])) | {'2026-11','2026-10','2025-01','2024-03'}, reverse=True)
def baselabel(c):return {'reported':'Reported','death':'Date of death','incident':'Incident date'}.get(c['date_basis'],'Atlas date')
def recorddate(c,fmt='%b %d, %Y'):
    label=pretty(c['atlas_date'],fmt)
    if c['date_basis']=='incident' and c['date_to'] and c['date_to']!=c['atlas_date']: label+=' – '+pretty(c['date_to'],fmt)
    return label
def layout(title,desc,url,body,section):
    nav=''.join(f'<a href="{path}"'+(' aria-current="page"' if section==key else '')+'>'+label+'</a>' for key,path,label in [('map','/','Explore the map'),('about','/about/','About the Atlas')])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · Catholic Incident Atlas</title><meta name="description" content="{e(desc)}"><meta name="atlas-revision" content="{e(os.environ.get('GITHUB_SHA', 'local'))}"><link rel="canonical" href="{ORIGIN+url}">
<meta property="og:title" content="{e(title)} · Catholic Incident Atlas"><meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{ORIGIN+url}"><meta name="twitter:card" content="summary_large_image"><meta property="og:image" content="{ORIGIN}/assets/share.jpg"><meta property="og:image:alt" content="Catholic Incident Atlas"><link rel="icon" href="/assets/logo.png"><link rel="stylesheet" href="/assets/atlas.css"><script src="/assets/atlas.js" defer></script></head><body>
<a class="skip" href="#main">Skip to content</a><header><div class="wrap mast"><a class="brand" href="/"><img src="/assets/logo.png" width="43" height="43" alt="">Catholic Incident Atlas</a><nav aria-label="Main navigation">{nav}</nav></div></header>
<main class="wrap" id="main">{body}</main><footer><div class="wrap foot"><span>Catholic Incident Atlas</span><div><a href="{REPO}">Research archive on GitHub</a><a href="https://x.com/IncidentAtlas">@IncidentAtlas</a></div></div></footer></body></html>'''
def monthpage(m):
    rows=[c for c in CASES if c['month']==m]
    month=monthname(m); countries=len({c['country'] for c in rows})
    mapped=sum(c['latitude'] is not None and c['longitude'] is not None for c in rows)
    options=''.join(f'<option value="{monthurl(x)}"'+(' selected' if x==m else '')+'>'+monthname(x)+'</option>' for x in months)
    cards=''
    for c in rows:
        tag=c['event_type']
        cards+=f'''<a class="case-card" href="{c['url']}" data-country="{e(c['country'])}" data-kind="{e(tag)}" data-query="{e(' '.join(str(c.get(k) or '') for k in ['title','locality','region','country','church','event_type','summary']).lower())}" data-key="{c['key']}">
        <div class="card-meta"><span class="type {slug(tag)}">{e(tag.title())}</span><span>{'Reported ' if c['date_basis']=='reported' else 'Death ' if c['date_basis']=='death' else ''}{recorddate(c,'%b %d')}</span></div><h3>{e(c['title'])}</h3><p>{icon('pin')}{e(c['place'])}, {e(c['country'])}</p></a>'''
    counts=Counter(c['event_type'] for c in rows)
    filters=''.join(f'<option value="{e(k)}">{e(k.title())} ({v})</option>' for k,v in sorted(counts.items()))
    points=[{k:c[k] for k in ('key','url','place','title','event_type','latitude','longitude')} for c in rows if c['latitude'] is not None and c['longitude'] is not None]
    body=f'''<div class="edition"><div><div class="overline"><i></i> Monthly atlas</div><h1>{month}</h1><p class="dek">Documented incidents affecting Catholic communities worldwide.</p></div>
    <div class="monthcontrol"><label for="month">Browse by month</label><div class="selectbox">{icon('calendar')}<select id="month">{options}</select>{icon('chev')}</div></div></div>
    <div class="dashboard"><section class="map-panel"><div class="maphead"><div class="panel-name">{icon('map')}<h2>Incident map</h2></div><span>Worldwide</span></div>
    <div class="mapstage" id="map" aria-label="Interactive world map of documented incidents"><div id="mapcanvas"></div>
    <div class="compass" aria-hidden="true"><b>N</b><svg width="23" height="35" viewBox="0 0 23 35"><path fill="#ebddba" d="m11.5 1 7 24-7-5z"/><path fill="#718c94" d="M11.5 1 4.5 25l7-5z"/></svg></div>
    <div class="maptools"><button id="zoomIn" aria-label="Zoom in">+</button><button id="zoomOut" aria-label="Zoom out">−</button><button id="reset" aria-label="Reset world view">{icon('locate')}</button></div>
    <noscript><p class="map-note">Open a case from the index to read its record.</p></noscript></div>
    <div class="legend"><span><i class="dot"></i> Recorded incident</span><span>Basemap · Natural Earth</span></div>
    <div class="metrics"><div><strong>{len(rows)}</strong><span>Recorded {'case' if len(rows)==1 else 'cases'}</span></div><div><strong>{countries}</strong><span>{'Country' if countries==1 else 'Countries'}</span></div><div><strong>{mapped}</strong><span>Mapped {'case' if mapped==1 else 'cases'}</span></div></div>
    <p class="map-caption">Select a marker or a case to read its sources. Points may represent a site, locality, or region. Counts reflect this Atlas collection with sources or assessments reviewed through {CUTOFF}.</p></section>
    <section class="index"><div class="indexhead"><div class="overline"><i></i> Case index</div><h2>Incident records</h2></div>
    <div class="filters"><div class="search">{icon('search')}<input type="search" id="search" aria-label="Search this month" placeholder="Search this month"></div><label class="filterbox"><select id="kind" aria-label="Filter by event type"><option value="">All types</option>{filters}</select>{icon('chev')}</label></div>
    <div class="list-label"><span id="count" aria-live="polite">{len(rows)} {'record' if len(rows)==1 else 'records'}</span><span>Newest first</span></div>
    <div class="cards">{cards}<p hidden id="empty">No matching cases this month. <button id="clear">Clear filters</button></p></div></section></div>
    <script type="application/json" id="points">{json.dumps(points).replace('<',chr(92)+'u003c')}</script>'''
    return layout(month+' incident map',f'Explore {len(rows)} documented cases across {countries} countries. Open a case for the Atlas assessment and original reporting.',monthurl(m),body,'map')
def casepage(c):
    basis=baselabel(c); m=monthname(c['month'])
    where=', '.join(dict.fromkeys(x for x in [c['locality'],c['region'],c['country']] if x))
    sources=sorted(c['sources'],key=lambda s:s['url']!=c['finding_source'])
    links=''.join(f'<li><div class="overline">{e(s["publisher"])}</div><a href="{e(s["url"])}">{e(s["title"])}</a>'+('<p>'+pretty(s['publication_date'])+'</p>' if s['publication_date'] else '')+'</li>' for s in sources)
    def facts(items):return '<dl>'+''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k,v in items if v)+'</dl>'
    info=facts([(basis,recorddate(c)),('Location',where),('Church or institution',c['church']),('Affected property',c['affected_property']),('Map precision',c['location_precision'].capitalize() if c['location_precision'] else 'Unmapped')])
    assessment=facts([('Cause',c['cause'].capitalize()),('Finding status',c['cause_status'].capitalize()),('Conduct',c['conduct'].capitalize()),('Negligence',c['negligence'].capitalize())])
    lead=next((s for s in sources if s['url']==c['finding_source']),None)
    firstsource=f'<a class="sourcebtn" href="{e(lead["url"])}">{icon("book")} Read the {e(lead["publisher"])} report</a>' if lead else ''
    body=f'''<div class="record-wrap"><a class="crumb" href="{monthurl(c['month'])}">{icon('map')} {m} map</a>
    <div class="overline"><i></i> Case record</div><h1>{e(c['title'])}</h1><div class="recordmeta"><span class="type {slug(c['event_type'])}">{e(c['event_type'].title())}</span><span>{e(c['place'])}, {e(c['country'])}</span><span>{basis} · {recorddate(c)}</span></div>
    <div class="readgrid"><article><section><h2>What happened</h2><p>{e(c['summary'])}</p>{firstsource}</section>
    <section><h2>What the evidence shows</h2><p>{e(c['evidence_note'])}</p>{assessment}{'<p>'+e(c['motive_note'])+'</p>' if c['motive_note'] else ''}</section>
    <section id="sources"><h2>Sources</h2><ol class="sourcelist">{links}</ol></section></article><aside><h2>Record details</h2>{info}<button class="copy" id="copy">{icon('link')} Copy case link</button><span role="status" id="copy-status"></span><p class="small">{('Assessment updated '+pretty(c['assessed_on'])+'.') if c['assessed_on'] else 'Assessment pending.'}<br>GitHub archive · Case {e(c['incident_id'])}.</p></aside></div></div>'''
    return layout(c['title'],c['summary'],c['url'],body,'')
for m in months:save(monthurl(m),monthpage(m))
save('/',monthpage((active_months or months)[0]))
for c in CASES:save(c['url'],casepage(c))
archive=''.join(f'<li><a href="{monthurl(m)}">{monthname(m)}</a></li>' for m in months)
body=f'''<div class="about"><div class="overline"><i></i> About the project</div><h1>About the Atlas</h1><p class="dek">A public record of incidents affecting Catholic people, property, and places of worship.</p>
<h2>What the Atlas counts</h2><p>Each record describes one researched event. The collection includes fires, thefts, assaults, and physical damage. An event’s inclusion says who or what was affected. Its cause and any evidence of a religious motive are recorded separately.</p>
<h2>How to read a case</h2><p>The monthly map uses the documented incident date when available. Records labeled “Reported” use the report date. When the only confirmed date is a death resulting from an incident, the record identifies that date explicitly. Each case appears once.</p><p>Markers may represent the site, locality, or a wider region. The case page gives the map precision, the latest recorded assessment, and links to the sources behind it. “Undetermined” means the available evidence leaves the question open.</p>
<h2>Coverage and sources</h2><p>This edition contains {len(CASES)} reviewed cases with sources or assessments reviewed through {CUTOFF}. Totals describe the cases documented so far. Reporting and research coverage vary by place and month.</p><p>The Atlas updates from reviewed records in the public GitHub database. Case links stay at the same address when an assessment, location, or date changes. Basemap geography comes from Natural Earth.</p><a href="{REPO}">Open the research archive on GitHub</a><h2>Monthly maps</h2><ul>{archive}</ul></div>'''
save('/about/',layout('About the Atlas','Scope, sources, date conventions, and monthly maps.','/about/',body,'about'))

# Retain a neutral landing page for records withdrawn or removed after publication.
current = {str(c['incident_id']):c['key'] for c in CASES}
known = {**{k:v['slug'] for k,v in links.items()}, **prior.get('links', {}), **current}
if len(set(known.values())) != len(known):
    raise ValueError("A case link is assigned to more than one incident")
for record_id, key in known.items():
    if record_id in current:
        if record_id in prior.get('links', {}) and current[record_id] != prior['links'][record_id]:
            raise ValueError("Existing case URL changed")
        continue
    url = '/cases/'+key+'/'
    save(url, layout('Case unavailable','This record is no longer published.',url,
                     '<div class="about"><h1>Case unavailable</h1><p>This case is no longer in the reviewed Atlas collection.</p><a href="/">Browse the current map</a></div>', ''))
(OUT / 'publication.json').write_text(json.dumps({'links':known, 'months':months, 'reviewed':len(CASES), 'commit':os.environ.get('GITHUB_SHA','local')}))
