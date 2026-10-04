import copy
import json
import shutil
from pathlib import Path
import pytest
from datafactory.research.export import export_research, make_tasks, snapshot
from datafactory.research.importer import import_research
from datafactory.research.resolution import classify_media, export_resolution_queues, research_task
from datafactory.research.schemas import ResultBundle
from datafactory.utils.atomic import atomic_json
from datafactory.utils.hashing import compute_sha256
from test_research_handoff import research_pack, image_result, inventory
from test_local_intelligence import candidate
from test_research_media_recovery import seed_existing, HoldRouter


FAILURES = [
    {'provider':'groq','status_category':'AI_QUOTA_DEFERRED','http_status':429,'error_class':'HTTP_RATE_LIMIT','rate_limited':True,'retryable':True,'timestamp':'2026-10-03T17:00:00+00:00'},
    {'provider':'gemini','status_category':'AI_UNAVAILABLE','http_status':503,'error_class':'HTTP_SERVER_ERROR','rate_limited':False,'retryable':True,'timestamp':'2026-10-03T17:01:00+00:00'}]


class UnavailableRouter(HoldRouter):
    def analyze(self,*args,**kwargs):
        return {'status':'AI_UNAVAILABLE','provider_failures':copy.deepcopy(FAILURES)}


def inputs():
    c=candidate(title='Garden.jpg')
    research={'status':'FOUND','result':{'source_page_url':c.source_url,'creator':c.creator,'license':c.license,
        'license_url':c.license_url,'attribution':c.attribution},'sources':[{'url':c.source_url}],'research_notes':''}
    decision={'action':'REVIEW','candidate':c.model_dump(),'checks':{'accepted':True,'sha256':'a'*64},
        'download':{'bytes':1000},'reason_codes':['AI_UNAVAILABLE','IDENTITY_EVIDENCE_INSUFFICIENT'],
        'ai':{'status':'AI_UNAVAILABLE','provider_failures':copy.deepcopy(FAILURES)}}
    return {'type':'REAL_PRIMARY_IMAGE'},research,decision


@pytest.mark.parametrize('city',['Jaipur','Udaipur','Varanasi','Manali','Shillong','Goa','Rishikesh'])
def test_valid_research_unavailable_provider_is_generic_retry(city):
    task,research,decision=inputs();task['city']={'name':city}
    record=classify_media(task,research,decision)
    assert record['resolution_state']=='PROVIDER_RETRY' and record['problem_type']=='ASSURANCE_HOLD'
    assert record['source_license_verified'] and not record['web_search_needed']
    assert [r['http_status'] for r in record['provider_failures']]==[429,503]


@pytest.mark.parametrize('status',['UNRESOLVED','PARTIAL','CONFLICT'])
def test_missing_or_conflicting_research_goes_to_web(status):
    task,research,decision=inputs();research.update(status=status)
    record=classify_media(task,research,decision)
    assert record['resolution_state']=='NEW_RESEARCH_REQUIRED' and record['problem_type']=='RESEARCH_GAP'


@pytest.mark.parametrize('notes',['Resolve place identity before selecting a primary image.','Identity must be resolved before reuse.','Treat as identity/policy review.','Do not attach this image until the place identity is resolved.','Identity should be resolved before attaching media.'])
def test_explicit_identity_conflict_is_manual(notes):
    task,research,decision=inputs();research.update(status='CONFLICT',research_notes=notes)
    record=classify_media(task,research,decision)
    assert record['resolution_state']=='MANUAL_REVIEW' and record['problem_type']=='IDENTITY_REVIEW'


def test_structural_identity_blocker_wins_over_provider_outage():
    task,research,decision=inputs()
    assert classify_media(task,research,decision,identity_blocked=True)['resolution_state']=='MANUAL_REVIEW'


@pytest.mark.parametrize('reason',['identity_mismatch','wrong_subject','poor_composition','watermark','composite_layout','interior_only'])
def test_wrong_identity_or_unsuitable_image_requires_alternative(reason):
    task,research,decision=inputs();decision['reason_codes'].append(reason)
    record=classify_media(task,research,decision)
    assert record['resolution_state']=='NEW_RESEARCH_REQUIRED' and record['alternate_image_required']


def test_false_checks_or_license_conflict_cannot_enter_provider_retry():
    task,research,decision=inputs();decision['checks']['accepted']=False
    assert classify_media(task,research,decision)['resolution_state']!='PROVIDER_RETRY'
    decision['checks']['accepted']=True;research['result']['license']='unknown free license'
    assert classify_media(task,research,decision)['resolution_state']!='PROVIDER_RETRY'


@pytest.mark.parametrize('reason',['DUPLICATE_OTHER_POI','HUMAN_FIELD_LOCK','SOURCE_BYTES_VERIFICATION_REQUIRED'])
def test_other_internal_blocker_cannot_be_hidden_by_provider_outage(reason):
    task,research,decision=inputs();decision['reason_codes'].append(reason)
    record=classify_media(task,research,decision)
    assert record['resolution_state']=='MANUAL_REVIEW' and not record['web_search_needed']


def test_contradictory_related_entity_requires_different_evidence():
    task,research,decision=inputs();task['place']={'wikidata_id':'Q100'};decision['candidate']['related_entity_id']='Q200'
    assert classify_media(task,research,decision)['resolution_state']=='NEW_RESEARCH_REQUIRED'


def test_unarchived_valid_candidate_requires_internal_review_not_web():
    task,_,decision=inputs()
    record=classify_media(task,None,decision)
    assert record['resolution_state']=='MANUAL_REVIEW' and not record['web_search_needed']


def test_registered_public_audit_preserves_provider_evidence_if_input_moved(research_pack):
    file=image_result(research_pack)
    import_research(file,settings=research_pack[0],apply=True,router=UnavailableRouter())
    settings,pack,_,output,*_=research_pack
    report=export_resolution_queues(pack,output/'queues',settings=settings)
    assert report['resolution_queues']['PROVIDER_RETRY']==1
    bundle=ResultBundle.model_validate_json((output/'queues/provider_retry/research_results.retry.json').read_text())
    assert bundle.results[0].result.source_page_url=='https://commons.wikimedia.org/wiki/File:Garden.jpg'
    assert bundle.results[0].sources and not bundle.results[0].result.local_file


def provider_history(fixture):
    settings,pack,place,output,*_=fixture
    source=image_result(fixture)
    archive=settings.data_dir/'research/import_inputs/provider.json';archive.parent.mkdir(parents=True)
    shutil.copyfile(source,archive)
    shutil.copytree(source.parent/'images',archive.parent/'images')
    report=import_research(archive,settings=settings,apply=True,router=UnavailableRouter())
    assert report['summary']['review']==1 and report['summary']['applied']==0
    return archive,report


def test_provider_queue_keeps_evidence_and_excludes_normal_web_export(research_pack):
    source,prior=provider_history(research_pack)
    settings,pack,place,output,*_=research_pack
    before=inventory(pack)
    queued=export_resolution_queues(pack,output/'queues',settings=settings)
    assert queued['resolution_queues']=={'PROVIDER_RETRY':1,'NEW_RESEARCH_REQUIRED':0,'MANUAL_REVIEW':0}
    retry=ResultBundle.model_validate_json((output/'queues/provider_retry/research_results.retry.json').read_text())
    original=ResultBundle.model_validate_json(source.read_text())
    assert retry.results[0].task_id==original.results[0].task_id and retry.results[0].result==original.results[0].result
    assert retry.results[0].sources==original.results[0].sources
    assert compute_sha256(output/'queues/provider_retry/images/garden.png')==compute_sha256(source.parent/'images/garden.png')
    dry=import_research(output/'queues/provider_retry/research_results.retry.json',settings=settings)
    assert dry['summary']['matched']==1 and dry['summary']['rejected']==0
    web=export_research(pack,output/'normal',settings=settings,types=['REAL_PRIMARY_IMAGE'],priorities=['P0'])
    assert web['total']==0 and web['excluded_resolution_queues']=={'PROVIDER_RETRY':1}
    assert before==inventory(pack)
    registry=settings.data_dir/'research/handoffs'/f"{web['handoff_id']}.json"
    registry_before=compute_sha256(registry)
    again=export_research(pack,output/'again',settings=settings,types=['REAL_PRIMARY_IMAGE'],priorities=['P0'])
    assert again['handoff_id']==web['handoff_id'] and compute_sha256(registry)==registry_before


def history_status(fixture,status,notes):
    source=image_result(fixture)
    data=json.loads(source.read_text());data['results'][0].update(status=status,research_notes=notes)
    data['results'][0]['result']={}
    archive=fixture[0].data_dir/'research/import_inputs/status.json';archive.parent.mkdir(parents=True)
    atomic_json(archive,data)
    import_research(archive,settings=fixture[0],apply=True,router=UnavailableRouter())


def test_new_research_export_is_registered_schema_valid_with_failure_context(research_pack):
    history_status(research_pack,'CONFLICT','The current candidate is a wrong-entity match.')
    settings,pack,_,output,*_=research_pack
    report=export_resolution_queues(pack,output/'queues',settings=settings)
    assert report['resolution_queues']['NEW_RESEARCH_REQUIRED']==1
    folder=output/'queues/new_research'
    template=ResultBundle.model_validate_json((folder/'research_results.template.json').read_text())
    assert len(template.results)==1 and template.results[0].status=='UNRESOLVED'
    assert json.loads((folder/'research_results.schema.json').read_text())==ResultBundle.model_json_schema()
    handoff=json.loads((folder/'research_handoff.json').read_text());task=handoff['tasks'][0]
    assert task['previous_attempt']['reason_codes']==['RESEARCH_CONFLICT']
    assert 'DO NOT return the previous candidate again' in task['research_instruction']
    assert task['known_evidence']['external_ids'] and task['place']['coordinates']
    md=(folder/'research_handoff.md').read_text(encoding='utf-8')
    assert 'Google Images' in md and 'source_page_url' in md and 'Do not guess' in md
    assert import_research(folder/'research_results.template.json',settings=settings)['summary']['matched']==1


def test_manual_review_export_does_not_enter_web_handoff(research_pack):
    history_status(research_pack,'CONFLICT','Resolve place identity before choosing a photograph.')
    settings,pack,_,output,*_=research_pack
    report=export_resolution_queues(pack,output/'queues',settings=settings)
    assert report['resolution_queues']['MANUAL_REVIEW']==1
    review=json.loads((output/'queues/manual_review/review_tasks.json').read_text())['tasks'][0]
    assert review['problem_type']=='IDENTITY_REVIEW' and review['current_research_status']=='CONFLICT'
    assert not json.loads((output/'queues/new_research/research_handoff.json').read_text())['tasks']
    assert export_research(pack,output/'normal',settings=settings,types=['REAL_PRIMARY_IMAGE'])['total']==0


def test_accepted_current_image_excluded_from_every_queue(research_pack):
    _,image,places=seed_existing(research_pack,verified=True)
    settings,pack,_,output,*_=research_pack
    image['license_url']='https://creativecommons.org/licenses/by-sa/4.0/'
    from datafactory.pipeline.media_assurance import media_signature
    atomic_json(pack/'places.json',places)
    assessed=json.loads((pack/'media_assurance.json').read_text())
    assessed[places[0]['id']]['media']['verification_hash']=media_signature(pack,image)
    atomic_json(pack/'media_assurance.json',assessed)
    report=export_resolution_queues(pack,output/'queues',settings=settings)
    assert report['total_remaining']==0 and not any(report['resolution_queues'].values())


def test_secrets_in_extra_diagnostics_or_local_data_are_not_exported(research_pack):
    _,prior=provider_history(research_pack)
    settings,pack,_,output,*_=research_pack
    history=next((settings.data_dir/'research/imports').glob('*.json'));data=json.loads(history.read_text())
    row=data['decisions'][0];row['ai']['provider_failures'][0]['response_body']='private-body-canary'
    row['ai']['authorization']='private-key-canary';row['local']['private_notes']='private-local-canary'
    atomic_json(history,data)
    export_resolution_queues(pack,output/'queues',settings=settings)
    all_text=''.join(p.read_text(encoding='utf-8') for p in (output/'queues').rglob('*') if p.suffix in {'.json','.md'})
    assert not any(s in all_text for s in ['private-body-canary','private-key-canary','private-local-canary'])


def test_queue_output_cannot_modify_a_release_or_use_stale_head(research_pack):
    settings,pack,place,output,*_=research_pack
    with pytest.raises(ValueError,match='cannot modify releases'):export_resolution_queues(pack,pack/'queues',settings=settings)
    from datafactory.research.export import city_key
    city=json.loads((pack/'city.json').read_text())
    atomic_json(settings.data_dir/'research/heads'/f"{city_key(city)}.json",{'output_pack':'india/rajasthan/jaipur/other','snapshot':snapshot(pack)})
    with pytest.raises(ValueError,match='latest research head'):export_resolution_queues(pack,output/'queues',settings=settings)


@pytest.mark.parametrize('aliases,preferences',[
    (['Astronomical Observatory'],['recognizable observatory instruments','closer framing','empty foreground']),
    (['Circle Park','Circle Garden'],['named park itself','generic garden photography','nearby landmark','fountain'])])
def test_card_suitability_hold_requests_better_composition_and_excludes_prior_sources(aliases,preferences):
    task,research,decision=inputs()
    task.update(city={'name':'Example city'},place={'name':'Example attraction','aliases':aliases,'category':'heritage'},
                known_evidence={'media_policy':'REAL_REQUIRED','existing_media':{'source_page':'https://commons.wikimedia.org/wiki/File:Existing.jpg'}})
    decision.update(unmet_requirements=['mobile_card_suitability'])
    decision['reason_codes'].append('MEDIA_ASSURANCE_THRESHOLD_NOT_MET')
    before=copy.deepcopy((task,research,decision))
    record=classify_media(task,research,decision)
    assert record['resolution_state']=='NEW_RESEARCH_REQUIRED' and record['alternate_image_required']
    record.update(previous_attempt={'source_page':research['result']['source_page_url'], 'unmet_requirements':decision['unmet_requirements']},
                  research_evidence=research,earlier_attempts=[{'source_page':'https://commons.wikimedia.org/wiki/File:Old.jpg'}])
    exported=research_task(task,record)
    assert 'DO NOT return the previous candidate again' in exported['research_instruction']
    assert all(value in exported['research_instruction'] for value in preferences)
    assert len(exported['known_evidence']['excluded_source_pages'])==3
    assert exported['known_evidence']['previous_research']==research
    assert (task,research,decision)==before


@pytest.mark.parametrize('name',['Elephant Riding','Camel rides','Boat ride'])
def test_generic_activity_gap_requires_identity_and_policy_review_without_changing_policy(name):
    task,research,decision=inputs()
    task.update(place={'name':name,'wikidata_id':None,'website':None},known_evidence={'media_policy':'REAL_REQUIRED'})
    research.update(status='UNRESOLVED',research_notes='Only generic activity imagery could be found; none tied to this exact listing.')
    before=copy.deepcopy(task)
    record=classify_media(task,research,decision)
    assert record['resolution_state']=='MANUAL_REVIEW' and record['problem_type']=='IDENTITY_REVIEW'
    assert record['review_flags']==['MEDIA_POLICY_REVIEW_RECOMMENDED', 'IDENTITY_REVIEW'] and not record['web_search_needed']
    assert task==before and task['known_evidence']['media_policy']=='REAL_REQUIRED'


def test_named_commercial_venue_keeps_exact_entity_research_and_flags_policy_without_substitution():
    task,research,decision=inputs()
    task.update(city={'name':'Example city'},place={'name':'Named elephant venue','aliases':[]},
                known_evidence={'media_policy':'REAL_REQUIRED'})
    research.update(status='UNRESOLVED',research_notes='The venue is verified but official/commercial gallery images were not assumed reusable.')
    record=classify_media(task,research,decision)
    assert record['resolution_state']=='NEW_RESEARCH_REQUIRED' and record['review_flags']==['MEDIA_POLICY_REVIEW_RECOMMENDED']
    record.update(previous_attempt={'source_page':None},research_evidence=research)
    exported=research_task(task,record)
    assert 'generic activity photograph is not evidence of this exact venue/entity' in exported['research_instruction']
    assert 'return UNRESOLVED' in exported['research_instruction']
    assert exported['known_evidence']['media_policy']=='REAL_REQUIRED'


def test_queue_handoff_changes_with_current_head_and_preserves_task_ids(research_pack):
    from datafactory.research.export import city_key
    settings,pack,place,output,*_=research_pack
    first=export_resolution_queues(pack,output/'first',settings=settings)
    first_task=json.loads((output/'first/new_research/research_handoff.json').read_text())['tasks'][0]
    newer=pack.parent/'v3-research-current-head'
    shutil.copytree(pack,newer)
    places=json.loads((newer/'places.json').read_text());places[0]['description']='Current head metadata'
    atomic_json(newer/'places.json',places)
    city=json.loads((newer/'city.json').read_text())
    atomic_json(settings.data_dir/'research/heads'/f"{city_key(city)}.json",{'output_pack':newer.relative_to(settings.releases_dir).as_posix(),'snapshot':snapshot(newer)})
    latest=export_resolution_queues(newer,output/'latest',settings=settings)
    last_task=json.loads((output/'latest/new_research/research_handoff.json').read_text())['tasks'][0]
    assert latest['new_research_handoff_id']!=first['new_research_handoff_id']
    assert latest['source_snapshot']==snapshot(newer)
    assert last_task['task_id']==first_task['task_id'] and last_task['place_id']==first_task['place_id']
    assert import_research(output/'latest/new_research/research_results.template.json',settings=settings)['summary']['matched']==1
