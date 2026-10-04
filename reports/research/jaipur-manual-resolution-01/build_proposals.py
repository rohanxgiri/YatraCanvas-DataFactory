"""Rebuild the six review artifacts from pinned source records; no source writes."""
import hashlib
import json
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

from datafactory.research.manual_resolution import (
    distance_m, identity_equivalence, preview_manual_changes, record_fingerprint,
)

ROOT = Path.cwd()
OUT = ROOT / 'data/research/manual_resolution/jaipur'
REPORT = ROOT / 'reports/research/jaipur-manual-resolution-01'
PACK = ROOT / 'releases/india/rajasthan/jaipur/v3-research-jaipur-images-03'
QUEUE = ROOT / 'data/research/exports/jaipur/required_images_round3/manual_review/review_tasks.json'
queue = json.loads(QUEUE.read_text(encoding='utf-8'))
places = json.loads((PACK / 'places.json').read_text(encoding='utf-8'))
by_id = {p['id']: p for p in places}
snapshot = {name: hashlib.sha256((PACK / name).read_bytes()).hexdigest() for name in queue['source_snapshot']}
assert snapshot == queue['source_snapshot'], 'STALE_SOURCE_SNAPSHOT'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def source(key, url, supports, strength='primary', limitation=None):
    row = dict(id=key, url=url, supports=supports, evidence_strength=strength)
    if limitation:
        row['limitation'] = limitation
    return row


osm = 'https://www.openstreetmap.org/'
wv = source('wikivoyage', 'https://en.wikivoyage.org/wiki/Jaipur',
            'The originating Jain Mandir listing names Bara Padampura; a separate listing names Sanghiji. The monuments section describes rooftop access opposite Isarlat.',
            'originating listing', 'The Jain Mandir coordinates and 15-16 km directions are unreliable; identity comes from the explicit listing text.')
municipal = source('suraj_municipal', 'https://pinkcity.jaipurmcheritage.org/Presentation/ExploreJaipur/OldGates.aspx',
                   'Surajpole is the eastern gateway of the old walled city, toward Galta and the Sun Temple.')
records = []


def add(slug, resolved_name, action, policy, tier, sources, reason, changes, confidence,
        image_need=False, blockers=None, excluded=None, classification=None):
    pid = 'yc_in_rj_jaipur_' + slug
    p = by_id[pid]
    task = next(t for t in queue['tasks'] if t['place_id'] == pid)
    external = dict(p['external_ids'])
    coords = dict(latitude=p['location']['latitude'], longitude=p['location']['longitude'])
    for key, value in changes.items():
        if key.startswith('external_ids.'):
            external[key.split('.')[1]] = value
        if key.startswith('location.'):
            coords[key.split('.')[1]] = value
    r = dict(place_id=pid, old_name=p['name'], resolved_name=resolved_name,
             resolution_status=action, confidence=confidence, identity_sources=sources,
             current_coordinates=p['location'], resolved_coordinates=coords,
             resolved_external_ids=external, current_aliases=p['alternate_names'],
             proposed_aliases=changes.get('alternate_names', p['alternate_names']),
             media_policy_recommendation=dict(current=task['media_policy'], recommended=policy,
                 reason=reason, applied=False),
             tier_review=dict(current_tier=p['tier'], recommended_tier=tier,
                 current_travel_relevance_score=p['travel_relevance_score'],
                 current_prominence_score=p['prominence_score'],
                 proposed_numeric_scores=None,
                 score_action='Recompute with normal deterministic classification after reviewed identity/region correction; do not carry confidence or prominence forward automatically.',
                 reason=reason, applied=False),
             classification_recommendation=classification,
             reasoning_summary=reason, proposed_field_changes=changes,
             image_search_needed_after_resolution=image_need,
             unresolved_questions=blockers or [], forbidden_substitutions=excluded or [],
             requires_human_review=True, applied=False,
             original_task_id_for_traceability_only=task['task_id'])
    records.append(r)
    return r


suraj = add('suraj_pol_gate', 'Suraj Pol Gate (Old Jaipur City)', 'KEEP', 'REAL_REQUIRED', 'core_destination', [
    source('suraj_osm', osm+'way/863303428', 'Exact old-city gate way; saved API geometry and historic=monument/name tags.'),
    source('suraj_wikidata', 'https://www.wikidata.org/wiki/Q140770830', 'City gate labelled Suraj Pol Gate Jaipur; P625 agrees with the old-city coordinates. P1435 records a state-protected designation.',
           'structured secondary', 'Protection designation is a Wikidata claim; no gazette notification independently verified.'),
    municipal,
    source('suraj_ignca', 'https://ignca.gov.in/asi_reports/RJJPR_358.pdf', 'Government heritage documentation identifies Suraj Pol in Pink City as a gateway.',
           limitation='Protection field is blank. Coarse coordinates and approach/orientation text are unsuitable for exact geolocation; municipal evidence and exact OSM/Wikidata anchors take precedence.'),
], 'A specifically identified walled-city heritage gate merits real entity-specific media. Core heritage treatment is defensible, but the exact 0.95 prominence is not independently established.',
    {'alternate_names': ['Surajpol Gate', 'Surajpole Gate', 'Suraj Pol (Old Jaipur City)'],
     'description': 'Suraj Pol, also called Surajpole Gate, is an eastern gateway of Jaipur\'s walled city on the route toward Galta and the Sun Temple.'},
    'High: exact OSM/Wikidata location plus municipal identity', True,
    excluded=['Amber Fort Suraj Pol / Sun Gate', 'Amber_Fort_-_Suraj_pol.jpg'], classification='Historic city gateway; retain heritage identity.')

jain = add('jain_mandir', 'Bada Padampura Jain Temple', 'RENAME', 'REAL_PREFERRED', 'recommended', [
    wv,
    source('padampura_venue', 'https://padampura.com/Contact', 'Temple trust identifies Padampura, Chaksu, Jaipur district and the Padamprabhu temple identity.',
           limitation='Address corroborates the region, not survey-level coordinates.'),
    source('padampura_wikidata_api', 'https://www.wikidata.org/wiki/Q121590708', 'Padampura entity P625 gives 26.7264,75.9386916667; exact entity was fetched via wbgetentities after Special:EntityData returned 403.', 'structured secondary'),
    source('padampura_wikipedia', 'https://en.wikipedia.org/wiki/Padampura', 'Temple identification and linked Q121590708 corroborate the intended listing.', 'secondary', 'Wikipedia and Wikidata are not independent coordinate measurements.'),
    source('padampura_map', 'https://api.openstreetmap.org/api/0.6/map?bbox=75.936,26.724,75.941,26.729', 'Nearby OSM node/7379872671 names Bara Padampura village.',
           limitation='This is a village object, not a temple ID; never assign it as the temple external ID.'),
    source('jain_current_nearby_map', 'https://api.openstreetmap.org/api/0.6/map?bbox=75.817,26.921,75.823,26.926',
           'Generic Jain Temple node/13275682430 is at 26.9237502,75.8199702, approximately 3 m from the current pin. This is material conflicting evidence: the old-city temple may be real, but it does not establish that the Bara Padampura listing describes that temple.'),
], 'The originating listing text and Shivdas Pura locality point to Bara/Bada Padampura, but a generic old-city Jain Temple OSM node lies approximately 3 m from the current pin. Thus the listing has conflicting components, not an obviously nonexistent temple. Propose correction to the explicitly described Padampura identity, subject to human confirmation of the intended record and regional scope. The Kanch Mandir, Indore enrichment is unrelated. A recommended regional religious destination with real-preferred media is more defensible than inheriting generic core status.',
    {'name':'Bada Padampura Jain Temple', 'name_en':'Bada Padampura Jain Temple',
     'alternate_names':['Bara Padampura Jain Temple', 'Padampura Jain Mandir'],
     'description':'Bada Padampura is a Jain pilgrimage temple dedicated to Padamprabhu in the Shivdaspura/Chaksu area of Jaipur district.',
     'location.latitude':26.7264, 'location.longitude':75.9386916667,
     'external_ids.wikidata_id':'Q121590708'},
    'High for listing-text identity; medium overall because the old-city pin also matches a generic temple', True,
    blockers=['Resolve the old-city temple versus Padampura listing conflict before any coordinate move; do not create or merge an old-city temple as a side effect.', 'Review the roughly 25 km coordinate move, precise entrance pin and regional association through normal geo assurance.', 'Shivdas Pura is a locality clue, not a precise temple alias; preserve it in provenance/history.', 'Reclassify heritage/attraction as a Jain religious temple through normal reviewed classification.'],
    excluded=['Sanghiji, Sanganer (Q24931166)', 'Kanch Mandir, Indore', 'Any nearby old-city temple chosen only by proximity'], classification='Religious / Jain temple; regional destination, subject to normal classification and geographic validation.')

haveli = add('haveli', None, 'UNRESOLVED', 'FALLBACK_ALLOWED', 'discovery', [
    source('haveli_osm', osm+'way/272782999', 'Exact geometry carries only name=Haveli and historic=yes; no proper name, palace type, public visitor access, or named operator.')
], 'The footprint is mapped, but the proper name, building use and visitor identity remain unknown. A generic historic=yes label does not support palace classification, core tier or 0.90 prominence. Hold identity and recommend discovery pending local evidence; this is not a claim that the building does not exist.',
    {}, 'Low for named visitor identity; high for exact OSM footprint',
    blockers=['Obtain a sign/address, heritage inventory cross-reference, or owner/municipal identity tied to this exact footprint.', 'No exact duplicate was established among existing named havelis.'],
    excluded=['Samode Haveli', 'Jaipur-Samode_Haveli-20131017.jpg'], classification='Unidentified historic building; palace/tourist-attraction classification unsupported.')

india = add('india_gate', 'India Gate (Sitapura)', 'DOWNGRADE', 'REAL_PREFERRED', 'recommended', [
    source('india_osm', osm+'node/3771356458', 'Exact India gate node at 26.7854254,75.8226628; historic=monument is an OSM contributor tag.'),
    source('india_transport', 'https://transport.rajasthan.gov.in/content/dam/transport/metro/Project/Suggestion%20on%20DPR%20Phase%202%20%26%20Phase%201C/2020.07.09_Final_DPR_Phase%202.pdf',
           'Official metro DPR identifies India Gate (SIA) along Tonk Road in the Sanganer/Sitapura context.',
           limitation='Supports local landmark name/context, not protected-monument status or attraction prominence; indexed DPR text reviewed, full 39 MB PDF not fetched.'),
], 'A real locally named India Gate landmark is supported in Sitapura. Evidence does not establish protected heritage or core visitor significance. Keep with locality qualifier and recommend a non-core landmark tier; retain real-preferred media without asserting that an unrelated decorative gate proves this entity.',
    {'name':'India Gate (Sitapura)', 'name_en':'India Gate (Sitapura)', 'alternate_names':['India gate'],
     'description':'India Gate is a locally named landmark in the Sitapura/Tonk Road area of southern Jaipur.'},
    'High for local place-name/location; medium for physical monument and visitor role', True,
    blockers=['Confirm the exact physical gate and current visitor relevance in future source research; municipal heritage/protection significance not established.'],
    excluded=['Patrika Gate', 'City Palace marble entrance', 'Jaipur,_India,_Gate.jpg'], classification='Local landmark; do not infer nationally significant monument from the name India Gate.')

elephant = add('elephant_riding', None, 'UNRESOLVED', 'FALLBACK_ALLOWED', 'discovery', [
    source('elephant_osm', osm+'node/5828540786', '2018 OSM node names Elephant village, English Elephant Riding, tourism=attraction and local contact/address tags; no stable operator or official venue ID.'),
    source('hathi_forest', 'https://forest.rajasthan.gov.in/content/raj/forest/hi/contact-us0/district-and-division-wise--forest---wildlife--control-room-help.html',
           'Forest department lists a Hathi Gaon range.', limitation='Does not establish equivalence between the reviewed OSM point and the government elephant village.'),
    source('elefantastic_official', 'https://www.elefantastic.in/',
           'The venue distinguishes its public office pin from the sanctuary location and publishes a different contact number from node/5828540786.',
           limitation='The published Elefantastic record is only 46.7 m away. Proximity and similar activities are not proof of a shared operator; contact differences do not conclusively prove separate ownership either.'),
], 'The source supports an elephant-related activity listing at Mahendi ka Bass, not a proven specific operator, government Hathi Gaon venue, or historic monument. Hold exact identity, recommend discovery/activity modeling, and remove the unrelated elephant-polo description only through later reviewed correction.',
    {'description':None}, 'Low for exact venue/operator; activity listing is source-supported',
    blockers=['Identify current operator, address and official venue evidence linked to node/5828540786.', 'Investigate nearby Elefantastic (46.7 m) using historical venue/contact evidence before any merge.', 'No exact equivalence to Hathi Gaon or either EleJungle record is established.'],
    excluded=['Arbitrary Amber Fort elephant-riding photo', 'EleJungle or Elefantastic without exact identity proof', 'Government Hathi Gaon by generic alias alone', 'Elephant polo'], classification='Activity/experience listing pending venue identification; not a historic monument.')

roof = add('rooftop_view_stairs', 'Rooftop viewpoint access stairs (Chandpol Bazaar)', 'DOWNGRADE', 'FALLBACK_ALLOWED', 'discovery', [
    source('rooftop_other_osm', osm+'node/11533709370', 'Exact staircase node matches existing coordinates and English name.'),
    source('rooftop_osm', osm+'node/12367918008', 'Nearby rooftop viewpoint node is about 32 m from the stairs; current canonical ID points here despite staircase coordinates.'),
    wv,
], 'A locally described rooftop viewpoint/access feature opposite Isarlat is supported, but a distinct named core monument is not. The source pack deduplicated two OSM nodes by 32 m proximity and name similarity. Recommend discovery micro-feature modeling, using the staircase object as canonical and retaining the viewpoint as a related source. Do not merge into the minaret across the road.',
    {'name':'Rooftop viewpoint access stairs (Chandpol Bazaar)', 'name_en':'Rooftop viewpoint access stairs (Chandpol Bazaar)',
     'description':'Metal-staircase access to a shopping-complex rooftop viewpoint across Chandpol Bazaar from Isarlat. Current public access should be checked before visiting.',
     'external_ids.osm_id':'node/11533709370'},
    'High for staircase versus viewpoint distinction; medium for current access',
    blockers=['The descriptive resolved label is not asserted to be an official proper name.', 'Confirm current public rooftop access before advertising it as a visitor experience.'],
    excluded=['Panna Meena ka Kund', 'Isarlat as the same physical feature'], classification='Viewpoint access / micro-feature, not a historic monument.')
roof['relation_recommendation'] = {'type':'access_to', 'target_external_id':'node/12367918008',
    'target_place_id':None, 'applied':False, 'reason':'Retain both OSM source objects in provenance; no second published viewpoint record found.'}

# Audit every published place, its aliases, IDs and original-source references.
con = sqlite3.connect((PACK/'city.db').resolve().as_uri()+'?mode=ro', uri=True)
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
duplicate_rows = []
candidate_words = {'suraj_pol_gate':['suraj','sun gate','amber fort','amer fort'],
    'jain_mandir':['jain','padampur','sanghiji'], 'haveli':['haveli'],
    'india_gate':['india gate','patrika','city palace'],
    'elephant_riding':['elephant','elefant','elejungle','hathi gaon','haathi'],
    'rooftop_view_stairs':['rooftop','isarlat','panna meena']}
for r in records:
    p = by_id[r['place_id']]
    words = candidate_words[r['place_id'].removeprefix('yc_in_rj_jaipur_')]
    candidates = []
    for q in places:
        if q['id'] == p['id']:
            continue
        text = json.dumps([q['name'],q['alternate_names']],ensure_ascii=False).casefold()
        same_ids = any(v and q['external_ids'].get(k)==v for k,v in r['resolved_external_ids'].items())
        source_ids = {s['source_id'] for s in q.get('sources', [])}
        if (same_ids or any(v in source_ids for v in r['resolved_external_ids'].values() if v)
                or any(w in text for w in words) or distance_m(p,q)<150):
            candidates.append({'place_id':q['id'], 'name':q['name'], 'aliases':q['alternate_names'],
                'coordinates':q['location'], 'external_ids':q['external_ids'],
                'offline_media':q['images'], 'source_references':q['sources'],
                'contact':q['contact'],
                'region_associations':q.get('region_associations', []),
                'equivalence_screen':identity_equivalence(p,q)})
    r['duplicate_audit'] = {'published_records_scanned':len(places),
        'exact_resolved_identity_duplicates':[q['id'] for q in places if q['id']!=p['id'] and
            any(v and q['external_ids'].get(k)==v for k,v in r['resolved_external_ids'].items())],
        'merge_proposed':False, 'candidate_count':len(candidates),
        'report':'duplicate_reference_audit.json'}
    duplicate_rows.append({'place_id':p['id'], 'aliases':p['alternate_names'],
        'coordinates':p['location'], 'external_ids':p['external_ids'],
        'offline_media':p['images'],
        'contact':p['contact'],
        'sqlite_media_rows':con.execute('SELECT count(*) FROM place_images WHERE place_id=?',(p['id'],)).fetchone()[0],
        'sqlite_source_rows':con.execute('SELECT count(*) FROM place_sources WHERE place_id=?',(p['id'],)).fetchone()[0],
        'relations':{'region_associations':p.get('region_associations',[]), 'source_references':p['sources'],
            'alternate_name_records':p['alternate_name_records'], 'provenance_records':p['provenance_records']},
        'trip_references':{'status':'not_available_in_this_pack', 'tables_checked':tables,
            'limitation':'No trip/itinerary/relationship table exists in the source SQLite schema. External consumer references are unknown; any future merge/removal needs that audit.'},
        'candidates':candidates, 'decision':'No identity-equivalent published target established; no merge proposed.'})
con.close()
save(OUT/'duplicate_reference_audit.json',dict(source_snapshot=snapshot, places_scanned=len(places), records=duplicate_rows))

bundle = {'schema_version':'1.0', 'kind':'manual_identity_proposals', 'apply_ready':False,
    'source_pack':queue['source_pack'], 'source_snapshot':snapshot,
    'scope':'Exactly six existing MANUAL_REVIEW records; identity proposals only.',
    'proposals':[]}
for r in records:
    bundle['proposals'].append(dict(place_id=r['place_id'], action=r['resolution_status'],
        before_sha256=record_fingerprint(by_id[r['place_id']]),
        changes=r['proposed_field_changes'], evidence=r['identity_sources'], reason=r['reasoning_summary'],
        media_policy_recommendation=r['media_policy_recommendation'], tier_review=r['tier_review'],
        classification_recommendation=r['classification_recommendation'],
        followup_requires=r['unresolved_questions'],
        provenance_rule='Append reviewed correction evidence; retain original sources, old values, rejected enrichments and history. Never overwrite immutable packs.'))
preview = preview_manual_changes(places, bundle, snapshot)
save(OUT/'proposed_changeset_01.json',bundle)
save(OUT/'proposed_changeset_01.dry_run.json',preview)
u = json.loads((PACK/'usability.json').read_text(encoding='utf-8'))
metrics = {k:u[k] for k in ['GENERAL_USABILITY','REAL_REQUIRED_MEDIA_COVERAGE','real_required_total','real_required_verified','critical_blockers','SOURCE_DATA_READY']}
save(OUT/'manual_resolution_01.json',dict(schema_version='1.0',kind='human_identity_resolution',
    status='PROPOSED_NOT_APPLIED',source_pack=queue['source_pack'],source_snapshot=snapshot,
    records=records, before=metrics, after=metrics,
    safety=dict(images_imported=0, paid_ai_calls=0, provider_calls=0, applied=0),
    limitations=['Exact monument protection notification not independently confirmed.',
                 'Existing incorrect media assignments remain unmodified in historical packs and are not newly verified.',
                 'Identity names can be resolved while precise geo/visitor significance remains subject to review.']))

tasks=[]
for r in records:
    if r['image_search_needed_after_resolution']:
        tasks.append(dict(place_id=r['place_id'],name=r['resolved_name'],
            type='PROPOSED_REAL_PRIMARY_IMAGE_RESEARCH',registered=False, apply_ready=False,
            priority='required' if r['media_policy_recommendation']['recommended']=='REAL_REQUIRED' else 'preferred',
            coordinates=r['resolved_coordinates'],external_ids=r['resolved_external_ids'],
            identity_sources=r['identity_sources'], exclude=r['forbidden_substitutions'],
            prerequisites=['Human review of identity/policy proposal.',
                'Reviewed source correction and normal geo/classification checks where needed.',
                'Fresh registered Research Handoff from the reviewed immutable source snapshot before any import.'],
            extra_review=r['unresolved_questions'],
            assurance='Exact entity, source creator/license/license URL, original media verification, MIME/dimensions, duplicates, SigLIP and existing FREE_ONLY assurance remain mandatory.'))
save(OUT/'manual_review_followup_image_tasks.json',dict(schema_version='1.0',kind='unregistered_image_research_proposals',
    registered=False,apply_ready=False,source_pack=queue['source_pack'],source_snapshot=snapshot,tasks=tasks,
    note='These are not registered task IDs and are not importable result bundles. Original manual-review task IDs are traceability only.'))

md=['# Jaipur manual identity resolution 01', '', '**Proposals only: no identity, tier, policy, media, release or handoff was changed.**',
    '', 'Source: `'+queue['source_pack']+'`. All 684 published records scanned for duplicate candidates.',
    '', 'Coverage remains **17/52 (32.69%)**; 35 required images remain unresolved. Policy recommendations do not alter the denominator.',
    '', '| Current POI | Resolved identity | Action | Recommended policy | Image research | Evidence |',
    '|---|---|---|---|---|---|']
for r in records:
    md.append('| '+' | '.join([r['old_name'], r['resolved_name'] or 'Exact identity unresolved',r['resolution_status'],r['media_policy_recommendation']['recommended'], 'Yes, after review' if r['image_search_needed_after_resolution'] else 'No task now',r['confidence']])+' |')
for r in records:
    md += ['', '## '+r['old_name'], '', '`'+r['place_id']+'`', '', r['reasoning_summary'],
        '', '**Current → proposed coordinates:** '+json.dumps(r['current_coordinates'])+' → '+json.dumps(r['resolved_coordinates']),
        '', '**Resolved source IDs:** `'+json.dumps(r['resolved_external_ids'])+'`',
        '', '**Tier review:** '+r['tier_review']['current_tier']+' → '+r['tier_review']['recommended_tier']+
        '; current travel relevance '+str(r['tier_review']['current_travel_relevance_score'])+
        ', prominence '+str(r['tier_review']['current_prominence_score'])+'. No replacement numeric scores invented.',
        '', '**Policy:** REAL_REQUIRED → '+r['media_policy_recommendation']['recommended']+' (recommendation, unapplied).',
        '', '**Classification:** '+r['classification_recommendation'], '', '**Evidence:**', '']
    for s in r['identity_sources']:
        md.append('- ['+s['id']+']('+s['url']+'): '+s['supports']+(' Limitation: '+s['limitation'] if s.get('limitation') else ''))
    md += ['', '**Remaining checks:** '+('; '.join(r['unresolved_questions']) or 'Normal human review and image assurance.'),
           '', '**Excluded substitutions:** '+ '; '.join(r['forbidden_substitutions'])]
md += ['', '## Duplicate/reference audit', '', 'No merges or removals proposed. Candidate identities, aliases, coordinates, source IDs, offline media and source/region relations are recorded in `duplicate_reference_audit.json`. No matching Padampura record exists in the published pack. External trip references are not available; their absence is not asserted.',
       '', 'The rooftop nodes are already represented by one published record; propose a canonical staircase-ID correction and preserve the other node as related provenance, not a new attraction or a merge into Isarlat.',
       '', '## Review workflow', '', 'The separate dry run validates snapshot/preconditions and emits detached diffs only. It does not certify factual accuracy or grant apply permission. Review identity, classification, region, tier and policy together; then use the normal curation/release workflow and generate a fresh registered image handoff. No existing importer or assurance code was changed.',
       '', '## Source access limitations', '', 'Padampura Special:EntityData returned HTTP 403; the public wbgetentities API succeeded. A broad Overpass lookup returned HTTP 504; small exact OSM bounding-box requests succeeded. The MEA PDF lookup failed DNS; the official transport DPR and OSM support the India Gate conclusion. IGNCA PDF text was read locally after the web reader returned a cache miss. Raw failure metadata is retained in evidence manifests.',
       '', '## Metrics', '', 'General usability remains 3.36%; REAL_REQUIRED coverage remains 32.69%; SOURCE_DATA_READY remains false. No proposed denominator changes are counted as image gains.', '']
(OUT/'manual_resolution_01.md').write_text('\n'.join(md),encoding='utf-8')
diff=['# Identity proposal dry run', '', 'STRUCTURALLY_VALID_PROPOSAL; applied=0, merged=0, deleted=0, media_assigned=0, policies_changed=0.', '']
for row in preview['rows']:
    diff += ['## '+row['place_id'], '', 'Action: '+row['proposed_action']+' (human review required).','']
    for d in row['field_diff']:
        diff.append('- `'+d['field']+'`: '+json.dumps(d['before'],ensure_ascii=False)+' → '+json.dumps(d['proposed_after'],ensure_ascii=False))
    if not row['field_diff']:diff.append('No identity fields proposed; retain unresolved status and review the separate tier/policy recommendation.')
    diff += ['', 'Separate policy recommendation: '+row['media_policy_recommendation']['recommended']+'; no policy applied.', '']
(OUT/'proposed_changeset_01.diff.md').write_text('\n'.join(diff),encoding='utf-8')
follow=['# Proposed follow-up image research', '', '**Unregistered; not importable; no handoff IDs or new task IDs assigned.**', '']
for t in tasks:
    follow += ['## '+t['name'], '', '- Place: `'+t['place_id']+'`', '- Priority: '+t['priority'],
               '- Coordinates (review required): '+json.dumps(t['coordinates']),
               '- Exclude: '+ '; '.join(t['exclude']),
               '- Before import: review identity, run geographic/classification checks, publish a separate reviewed source pack if needed, and generate a fresh registered handoff.', '']
follow += ['Haveli and Elephant Riding need identity evidence first. The rooftop stairs are proposed as a discovery micro-feature with no required photo task. All six existing records and their policies remain unchanged.','']
(OUT/'manual_review_followup_image_tasks.md').write_text('\n'.join(follow),encoding='utf-8')
print(json.dumps({'resolution_records':len(records),'proposals':preview['proposals'],'followup_image_tasks':len(tasks),'applied':0}))
