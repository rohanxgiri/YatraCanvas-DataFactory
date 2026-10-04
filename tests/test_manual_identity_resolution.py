"""Regression guards for proposal-only identity review, independent of releases."""
import copy
import json

import pytest

from datafactory.research.manual_resolution import (
    identity_equivalence, preview_manual_changes, record_fingerprint,
)


def place(pid, name, lat, lon, osm=None, qid=None, aliases=()):
    return {'id':pid, 'name':name, 'name_en':name, 'description':None,
            'alternate_names':list(aliases), 'location':{'latitude':lat,'longitude':lon},
            'external_ids':{'osm_id':osm,'wikidata_id':qid},
            'images':{'primary':{'local_path':'images/retained.webp'}},
            'tier':'core_destination','media_policy':'REAL_REQUIRED'}


# Real source anchors and wrong substitutions from the six-record Jaipur review.
@pytest.mark.parametrize('left,right', [
    (place('suraj','Suraj Pol',26.919156,75.844935,'way/863303428','Q140770830'),
     place('amber','Suraj Pol',26.986723,75.851357,'node/5079237889')),
    (place('jain','Jain Mandir',26.923767,75.819993,aliases=['Shivdas Pura']),
     place('sanghiji','Jain Mandir',26.815,75.786111,qid='Q24931166')),
    (place('haveli','Haveli',26.920539,75.818882,'way/272782999'),
     place('samode','Samode Haveli',26.933104,75.837257,'node/4959426923',aliases=['Haveli'])),
    (place('india','India gate',26.785425,75.822663,'node/3771356458'),
     place('patrika','Patrika Gate',26.841507,75.801365,'way/864605414')),
    (place('elephant','Elephant Riding',26.986715,75.866135,'node/5828540786',aliases=['Elephant village']),
     place('operator','Elephant Riding',26.994224,75.877945,'node/12909037307')),
    (place('rooftop','Rooftop view stairs',26.923816,75.820661,'node/12367918008'),
     place('panna','Panna Meena ka Kund',26.991208,75.851227,'way/410063780','Q97119522')),
], ids=['old_city_suraj_not_amber','jain_not_sanghiji','haveli_not_samode',
        'india_not_patrika','activity_not_exact_operator','stairs_not_panna_meena'])
def test_wrong_substitution_cannot_qualify_for_merge(left, right):
    before = copy.deepcopy((left,right))
    result = identity_equivalence(left,right)
    assert not result['eligible_for_merge_review']
    assert 'NO_SHARED_EXACT_IDENTITY' in result['reason_codes']
    assert (left,right) == before


def test_same_name_at_same_pin_without_exact_ids_is_not_identity_proof():
    left=place('a','Elephant village',26.98,75.86)
    right=place('b','Elephant village',26.98,75.86)
    assert identity_equivalence(left,right)['reason_codes'] == ['NO_SHARED_EXACT_IDENTITY']


def test_same_osm_id_does_not_hide_conflicting_wikidata():
    left=place('a','Gate',26.9,75.8,'node/1','Q1')
    right=place('b','Gate',26.9,75.8,'node/1','Q2')
    assert 'CONFLICTING_EXTERNAL_IDS' in identity_equivalence(left,right)['reason_codes']


def test_same_id_with_remote_pin_requires_coordinate_review():
    left=place('a','Temple',26.923767,75.819993,qid='Q121590708')
    right=place('b','Padampura',26.7264,75.938692,qid='Q121590708')
    assert 'COORDINATE_CONFLICT_REQUIRES_REVIEW' in identity_equivalence(left,right)['reason_codes']


@pytest.fixture
def review():
    places=[place('a','Gate',26.9,75.8,'node/1'),place('b','Gate alias',26.90001,75.8,'node/1')]
    snapshot={'places.json':'test-digest'}
    proposal={'place_id':'a','action':'RENAME','before_sha256':record_fingerprint(places[0]),
              'changes':{'name':'Old City Gate'},
              'evidence':[{'url':'https://www.openstreetmap.org/node/1','supports':'Exact object identity'}],
              'reason':'Disambiguate a locality-qualified name.',
              'media_policy_recommendation':{'current':'REAL_REQUIRED','recommended':'REAL_PREFERRED',
                   'reason':'Proposed non-core landmark modeling.','applied':False},
              'tier_review':{'recommended_tier':'recommended','applied':False}}
    bundle={'kind':'manual_identity_proposals','schema_version':'1.0','apply_ready':False,
            'source_snapshot':snapshot.copy(),'proposals':[proposal]}
    return places,bundle,snapshot


def test_preview_is_non_mutating_and_returned_values_are_detached(review):
    places,bundle,snapshot=review
    original=copy.deepcopy(review)
    result=preview_manual_changes(*review)
    assert result['applied']==result['deleted']==result['merged']==result['media_assigned']==0
    assert result['policies_changed']==0
    assert result['rows'][0]['field_diff']==[{'field':'name','before':'Gate','proposed_after':'Old City Gate'}]
    result['rows'][0]['media_policy_recommendation']['recommended']='REMOVE_POI'
    result['rows'][0]['tier_review']['recommended_tier']='discovery'
    assert review==original


@pytest.mark.parametrize('action',['MERGE','REMOVE'])
def test_destructive_actions_remain_proposals_and_preserve_media_and_references(review,action):
    places,bundle,snapshot=review
    item=bundle['proposals'][0]
    item.update(action=action,changes={})
    if action=='MERGE':
        item.update(target_place_id='b',target_before_sha256=record_fingerprint(places[1]),
            reference_audit={k:'reviewed' for k in ['aliases','coordinates','external_ids','offline_media','trip_references','relations']})
    original=copy.deepcopy(review)
    result=preview_manual_changes(*review)
    assert result['applied']==result['merged']==result['deleted']==0
    assert len(places)==2 and places[0]['images']['primary']
    assert review==original
    assert result['rows'][0]['requires_human_review']


@pytest.mark.parametrize('field',['media_policy','tier','prominence_score','images.primary','id','sources'])
def test_policy_and_protected_fields_cannot_be_smuggled_into_identity_changes(review,field):
    review[1]['proposals'][0]['changes'][field]='arbitrary'
    with pytest.raises(ValueError,match='FIELD_OUTSIDE_IDENTITY_PROPOSAL_SCOPE'):
        preview_manual_changes(*review)


def test_media_recommendation_cannot_claim_to_be_applied(review):
    review[1]['proposals'][0]['media_policy_recommendation']['applied']=True
    with pytest.raises(ValueError,match='SEPARATE_UNAPPLIED_POLICY'):
        preview_manual_changes(*review)


@pytest.mark.parametrize('part',['snapshot','record','duplicate','evidence','format'])
def test_stale_or_untraceable_proposal_fails_closed(review,part):
    places,bundle,snapshot=review
    if part=='snapshot':snapshot['places.json']='new-digest'
    if part=='record':places[0]['name']='Edited after research'
    if part=='duplicate':bundle['proposals']*=2
    if part=='evidence':bundle['proposals'][0]['evidence']=[]
    if part=='format':bundle['apply_ready']=True
    before=copy.deepcopy(review)
    with pytest.raises(ValueError):preview_manual_changes(*review)
    assert review==before


@pytest.mark.parametrize('problem',['unknown_target','self_target','stale_target','references_unknown','wrong_identity'])
def test_incomplete_or_wrong_merge_is_blocked(review,problem):
    places,bundle,snapshot=review
    item=bundle['proposals'][0]
    item.update(action='MERGE',changes={},target_place_id='b',
        target_before_sha256=record_fingerprint(places[1]),
        reference_audit={k:'reviewed' for k in ['aliases','coordinates','external_ids','offline_media','trip_references','relations']})
    if problem=='unknown_target':item['target_place_id']='missing'
    if problem=='self_target':item['target_place_id']='a'
    if problem=='stale_target':places[1]['name']='changed'
    if problem=='references_unknown':item['reference_audit']['trip_references']='unknown'
    if problem=='wrong_identity':
        places[1]['external_ids']['osm_id']='node/999'
        item['target_before_sha256']=record_fingerprint(places[1])
    with pytest.raises(ValueError):preview_manual_changes(*review)


def test_preview_does_not_write_source_files(tmp_path,review):
    source=tmp_path/'places.json'
    source.write_text(json.dumps(review[0]),encoding='utf-8')
    before=source.read_bytes()
    preview_manual_changes(*review)
    assert source.read_bytes()==before
    assert list(tmp_path.iterdir())==[source]
