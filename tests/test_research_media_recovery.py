import copy
import hashlib
import io
import json
import shutil
import unicodedata
import subprocess
import sys
from pathlib import Path
import httpx
import pytest
from PIL import Image
from datafactory.ai.router import digest, AIRouter
from datafactory.ai.providers import GroqProvider, GeminiProvider, AIError
from datafactory.models.media_candidate import MediaCandidate
from datafactory.pipeline.identity_assurance import compact_identity
from datafactory.pipeline.image_content import normalize_primary_frame, ImageContentError
from datafactory.utils.media_metadata import canonical_license, canonical_license_url, commons_filename, creator_key
from datafactory.pipeline.media_assurance import MediaAssurance, deterministic_filter, media_signature
from datafactory.research.media_evidence import ResearchMediaEvidence, merge_research_media_evidence
from datafactory.research.importer import import_research
from datafactory.research.export import export_research
from datafactory.research.retry import build_retry_bundle
from datafactory.research.schemas import ResultBundle
from datafactory.sources.wikimedia import WikimediaCommonsClient
from datafactory.utils.atomic import atomic_json
from datafactory.utils.cache import DiskCache
from test_research_handoff import research_pack, image_result
from test_local_intelligence import photo, candidate
from test_ai_assurance import config, MEDIA, Fake


class HoldRouter:
    def analyze(self, *args, **kwargs):
        return {"status": "MEDIA_VERIFICATION_REQUIRED"}
    def report(self):
        return {"AI_MODE": "FREE_ONLY", "stats": {"calls": 0}, "paid_feature_calls": 0, "paid_providers_invoked": 0}


class AcceptRouter(HoldRouter):
    def analyze(self, *args, **kwargs):
        return {"status": "OK", "result": copy.deepcopy(MEDIA)}


def seed_existing(fixture, *, gallery=False, verified=False, author="Photographer"):
    settings, pack, place, output, *_ = fixture
    file = image_result(fixture)
    places = json.loads((pack / "places.json").read_text(encoding="utf-8"))
    pid = place["id"]
    paths = [f"images/{pid}/primary.webp", f"images/{pid}/thumbnail.webp"]
    for relative, size in zip(paths, [(800, 600), (400, 300)]):
        path = pack / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(io.BytesIO(photo())) as image:
            image.thumbnail(size)
            image.save(path, "WEBP", quality=85)
    image = {"image_type":"real", "source":"Wikimedia Commons", "source_page":"https://commons.wikimedia.org/wiki/File:Garden.jpg",
        "original_file":"Garden.jpg", "author":author, "license":"CC BY-SA 4.0",
        "license_url":None if verified else "https://creativecommons.org/licenses/by-sa/4.0/",
        "attribution":"Photographer / CC BY-SA 4.0", "local_path":paths[0], "thumbnail_path":paths[1],
        "width":800, "height":600, "match_method":"commons_category", "match_confidence":.92,
        "content_sha256":hashlib.sha256(photo()).hexdigest(), "downloaded_at":"2026-01-01T00:00:00Z"}
    places[0]["images"]["primary"] = None if gallery else image
    places[0]["images"]["gallery"] = [image] if gallery else []
    atomic_json(pack / "places.json", places)
    assessed = {pid:{"media":{"verified":verified,"candidates":[]}}}
    if verified:
        assessed[pid]["media"].update(identity_hash=digest(compact_identity(places[0])), verification_hash=media_signature(pack,image))
    atomic_json(pack / "media_assurance.json", assessed)
    new = export_research(pack, output / "refreshed", types=["REAL_PRIMARY_IMAGE"], priorities=["P0"], settings=settings)
    data = json.loads(file.read_text(encoding="utf-8"));data["handoff_id"]=new["handoff_id"];atomic_json(file,data)
    return file, image, places


@pytest.mark.parametrize("gallery", [False, True])
def test_same_researched_primary_or_gallery_reuses_bytes_and_upgrades_provenance(research_pack, gallery):
    file, old, _ = seed_existing(research_pack, gallery=gallery)
    settings, source, *_ = research_pack
    original_hash = hashlib.sha256((source / old["local_path"]).read_bytes()).hexdigest()
    report = import_research(file, settings=settings, apply=True, router=AcceptRouter())
    assert report["summary"]["applied"] == 1
    row=report["decisions"][0]
    assert "EXISTING_ASSET_REUSE" in row["reason_codes"] and "DUPLICATE_IMAGE" not in row["reason_codes"]
    output=Path(report["output_pack"])
    assert hashlib.sha256((output / old["local_path"]).read_bytes()).hexdigest()==original_hash
    assert hashlib.sha256((source / old["local_path"]).read_bytes()).hexdigest()==original_hash
    assert json.loads((output/'media_assurance.json').read_text())[old_id(research_pack)]["media"]["verified"]
    assert json.loads((output/'field_provenance.json').read_text())[0]["task_id"] == row["task_id"]
    assert json.loads((output/'places.json').read_text())[0]["images"]["primary"]["match_method"] == "commons_category"


def old_id(fixture):
    return fixture[2]["id"]


def test_existing_identity_bound_asset_avoids_cloud_and_dry_run_has_no_mutation(research_pack):
    file, image, _ = seed_existing(research_pack, verified=True)
    from test_research_handoff import inventory
    before=inventory(research_pack[0].project_root)
    dry=import_research(file,settings=research_pack[0])
    assert dry["summary"]["auto_applicable"]==1
    assert before==inventory(research_pack[0].project_root)
    report=import_research(file,settings=research_pack[0],apply=True,router=HoldRouter())
    assert report["summary"]["applied"]==1
    assert "REUSE_EXISTING_VERIFIED_ASSET" in report["decisions"][0]["reason_codes"]
    assert report["local_intelligence"]["cloud_jobs_avoided"]==1
    assert report["ai_usage"]["stats"]["calls"]==0


def test_verified_existing_conflicting_creator_stays_review(research_pack):
    file, _, _ = seed_existing(research_pack,verified=True,author="Different creator")
    report=import_research(file,settings=research_pack[0],apply=True,router=AcceptRouter())
    assert report["summary"]["applied"]==0
    assert "VERIFIED_EXISTING_METADATA_CONFLICT" in report["decisions"][0]["reason_codes"]


def test_same_bytes_other_poi_and_near_duplicate_other_source_stay_review(research_pack):
    file, image, places=seed_existing(research_pack)
    settings, pack, *_=research_pack
    other=copy.deepcopy(places[0]);other['id']='another_poi';other['name']='Unrelated place';other['external_ids']={}
    context=ResearchMediaEvidence([places[0],other],{},pack)
    probe=candidate(title='Garden.jpg')
    assert context.existing(places[0],probe,photo())['conflict']=='DUPLICATE_OTHER_POI'
    places[0]['images']['primary']['source_page']='https://commons.wikimedia.org/wiki/File:Other.jpg'
    places[0]['images']['primary']['original_file']='Other.jpg'
    context=ResearchMediaEvidence([places[0]],{},pack)
    assert context.existing(places[0],probe,photo(variant=1))['conflict']=='DUPLICATE_OTHER_ASSET'


def test_exact_same_poi_local_bytes_are_reusable(research_pack):
    _, image, places = seed_existing(research_pack)
    pack = research_pack[1]
    content = (pack / image['local_path']).read_bytes()
    context = ResearchMediaEvidence(places, {}, pack)
    assert context.existing(places[0], candidate(title='Garden.jpg'), content)['asset']['path'] == pack / image['local_path']


def test_existing_proof_cannot_override_contradictory_entity(research_pack,tmp_path):
    place=research_pack[2];content=photo();c=candidate(title='Garden.jpg');c.related_entity_id='Q999999'
    proof={'place_id':place['id'],'identity_hash':digest(compact_identity(place)),
           'content_sha256':hashlib.sha256(content).hexdigest(),'source_key':'Garden.jpg'}
    assessment=MediaAssurance({},HoldRouter(),tmp_path).assess(place,c,content,existing_verification=proof)
    assert assessment['action']=='REJECT' and assessment['reason_codes']==['CONTRADICTORY_ENTITY_EVIDENCE']


def test_existing_verification_cannot_override_current_identity_blocker(research_pack):
    _, image, places=seed_existing(research_pack,verified=True)
    pack=research_pack[1];pid=places[0]['id']
    assurance=json.loads((pack/'media_assurance.json').read_text());assurance[pid]['identity_blocker']='ENTITY_CONFLICT'
    context=ResearchMediaEvidence(places,assurance,pack)
    assert context.existing(places[0],candidate(title='Garden.jpg'),photo())['verified_identity'] is None


def test_verified_original_filename_conflict_stays_review(research_pack):
    _, image, places=seed_existing(research_pack,verified=True)
    pack=research_pack[1];pid=places[0]['id'];image['original_file']='Different.jpg'
    assurance=json.loads((pack/'media_assurance.json').read_text())
    assurance[pid]['media']['verification_hash']=media_signature(pack,image)
    context=ResearchMediaEvidence(places,assurance,pack)
    assert context.existing(places[0],candidate(title='Garden.jpg'),photo())['conflict']=='VERIFIED_EXISTING_METADATA_CONFLICT'


@pytest.mark.parametrize('wrong_qid',[False,True])
def test_actual_p18_claim_preserves_linkage_and_authoritative_path(research_pack,monkeypatch,wrong_qid):
    file=image_result(research_pack);place=research_pack[2];qid=place['external_ids']['wikidata_id']
    DiskCache('wikidata').set('entity_'+qid,{'wikidata_id':'Q999999' if wrong_qid else qid,'p18_image':'Garden.jpg'})
    monkeypatch.setattr(MediaAssurance,'download',lambda self,c:photo())
    report=import_research(file,settings=research_pack[0],apply=True,allow_network=True,router=HoldRouter())
    row=report['decisions'][0]
    if wrong_qid:
        assert report['summary']['applied']==0 and row['candidate']['match_method']!='wikidata_p18'
    else:
        assert report['summary']['applied']==1 and row['candidate']['match_method']=='wikidata_p18'
        assert row['candidate']['related_entity_id']==qid and row['candidate']['original_license_verified'] is True
        assert 'VERIFIED_ENTITY_LINKED_P18' in row['reason_codes'] and report['ai_usage']['stats']['calls']==0


def test_p18_cannot_authorize_unrelated_local_bytes(research_pack,monkeypatch):
    file=image_result(research_pack);place=research_pack[2];qid=place['external_ids']['wikidata_id']
    DiskCache('wikidata').set('entity_'+qid,{'wikidata_id':qid,'p18_image':'Garden.jpg'})
    monkeypatch.setattr(MediaAssurance,'download',lambda self,c:photo(variant=40))
    report=import_research(file,settings=research_pack[0],apply=True,allow_network=True,router=AcceptRouter())
    assert report['summary']['applied']==0 and 'SOURCE_BYTES_VERIFICATION_REQUIRED' in report['decisions'][0]['reason_codes']


@pytest.mark.parametrize('method',['wikipedia_lead','commons_category','commons_exact_name_search','wikivoyage_listing_image','openverse_original_commons'])
def test_exact_known_source_method_is_preserved(research_pack,method):
    file=image_result(research_pack);result=ResultBundle.model_validate_json(file.read_text()).results[0]
    info=WikimediaCommonsClient(read_only=True).cached_image_info('Garden.jpg')
    known=MediaCandidate.from_commons(info,method,.94)
    merged,_=merge_research_media_evidence([known],result.result,info,research_pack[2])
    assert merged.match_method==method and merged.source_confidence==.95
    known.related_entity_id='Q999999'
    assert merge_research_media_evidence([known],result.result,info,research_pack[2])[0] is None


def mpo():
    stream=io.BytesIO()
    with Image.open(io.BytesIO(photo(fmt='JPEG'))) as first,Image.open(io.BytesIO(photo(fmt='JPEG',variant=20))) as second:
        first.save(stream,'MPO',save_all=True,append_images=[second])
    return stream.getvalue()


def test_mpo_primary_frame_normalizes_and_normal_jpeg_is_unchanged():
    original=mpo();normalized,codes=normalize_primary_frame(original)
    assert codes==['MPO_PRIMARY_FRAME_NORMALIZED']
    with Image.open(io.BytesIO(normalized)) as image:assert image.format=='WEBP' and image.size==(800,600)
    assert deterministic_filter(candidate(),original)['accepted']
    jpeg=photo(fmt='JPEG');assert normalize_primary_frame(jpeg)==(jpeg,[])
    with pytest.raises(ImageContentError,match='IMAGE_BYTES_EXCEEDED'):normalize_primary_frame(original,max_bytes=100)
    with pytest.raises(ImageContentError,match='IMAGE_DECODE_BUDGET_EXCEEDED'):normalize_primary_frame(original,max_pixels=100)
    assert not deterministic_filter(candidate(),original[:len(original)//4])['accepted']


def test_mpo_import_continues_through_assurance_and_offline_webp(research_pack):
    file=image_result(research_pack)
    (file.parent/'images/garden.png').write_bytes(mpo())
    report=import_research(file,settings=research_pack[0],apply=True,router=AcceptRouter())
    assert report['summary']['applied']==1
    assert 'MPO_PRIMARY_FRAME_NORMALIZED' in report['decisions'][0]['reason_codes']
    output=Path(report['output_pack']);p=json.loads((output/'places.json').read_text())[0]
    with Image.open(output/p['images']['primary']['local_path']) as image:assert image.format=='WEBP'


def test_mpo_huge_header_dimensions_reject_before_pixel_allocation():
    content=bytearray(mpo());marker=content.index(b'\xff\xc0')
    content[marker+5:marker+7]=(6000).to_bytes(2,'big')
    content[marker+7:marker+9]=(8000).to_bytes(2,'big')
    with Image.open(io.BytesIO(content)) as image:assert image.format=='MPO' and image.size==(8000,6000)
    with pytest.raises(ImageContentError,match='IMAGE_DECODE_BUDGET_EXCEEDED'):normalize_primary_frame(bytes(content))


@pytest.mark.parametrize('name,expected',[('CC0','CC0 1.0'),('CC0 1.0','CC0 1.0'),('Creative Commons CC0 1.0','CC0 1.0'),('CC BY 4.0','CC BY 4.0'),('CC-BY-4.0','CC BY 4.0'),('CC BY-SA 4.0','CC BY-SA 4.0'),('unknown free license',None)])
def test_finite_license_names(name,expected):assert canonical_license(name)==expected


@pytest.mark.parametrize('path',['licenses/by/4.0','licenses/by-sa/4.0','publicdomain/zero/1.0'])
@pytest.mark.parametrize('ending',['','/','/deed.en','/legalcode'])
def test_only_known_cc_urls_upgrade_to_https(path,ending):
    assert canonical_license_url('http://creativecommons.org/'+path+ending)=='https://creativecommons.org/'+path+'/'
    assert canonical_license_url('https://creativecommons.org/'+path+ending)=='https://creativecommons.org/'+path+'/'
    assert canonical_license_url('http://unrelated.example/'+path+ending) is None
    assert canonical_license_url('http://creativecommons.org/'+path+'/unexpected') is None


def test_license_version_conflicts_and_creator_names_remain_distinct():
    assert canonical_license('CC BY 4.0','https://creativecommons.org/licenses/by/3.0/') is None
    assert canonical_license('CC BY','https://creativecommons.org/licenses/by/4.0/')=='CC BY 4.0'
    name='Jakub Hałun';assert creator_key(name)==creator_key(unicodedata.normalize('NFD',name))
    assert creator_key(name)!=creator_key('Jakub Halun')
    assert canonical_license_url('http://creativecommons.org.evil.example/licenses/by/4.0/') is None
    assert canonical_license_url('http://creativecommons.org/licenses/by/4.0/?redirect=evil') is None


@pytest.mark.parametrize('encoded,expected',[('Moti_Doongri_Fort,_Jaipur;_January_2024.jpg','Moti Doongri Fort, Jaipur; January 2024.jpg'),('A%20B_(C),_D%27s.jpg',"A B (C), D's.jpg"),('नमस्ते_%25_%3B.jpg','नमस्ते % ;.jpg'),('A%2520B.jpg','A%20B.jpg')])
def test_commons_filename_decodes_once_without_losing_punctuation(encoded,expected):
    assert commons_filename('https://commons.wikimedia.org/wiki/File:'+encoded,source_url=True)==expected


def derivative_media(monkeypatch,tmp_path,*,oversized=False,available=True,derivative_large=False):
    import datafactory.pipeline.media_assurance as module
    body=photo(fmt='JPEG');calls=[];real_client=httpx.Client
    def handler(request):
        calls.append(str(request.url))
        if '/thumb/' in request.url.path:
            return httpx.Response(200,headers={'content-type':'image/jpeg','content-length':str(20_000_001 if derivative_large else len(body))},content=body)
        return httpx.Response(200,headers={'content-type':'image/jpeg','content-length':str(20_000_001 if oversized else len(body))},content=body)
    monkeypatch.setattr(module.httpx,'Client',lambda **kw:real_client(transport=httpx.MockTransport(handler),**kw))
    media=MediaAssurance({},HoldRouter(),tmp_path,allow_network=True)
    media.commons.get_derivative_info=lambda filename,edge:{'url':'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Garden.jpg/800px-Garden.jpg','width':800,'height':600,'original_file':'Garden.jpg'} if available else None
    return media,body,calls


@pytest.mark.parametrize('oversized,available,derivative_large,success,used',[(False,True,False,True,False),(True,True,False,True,True),(True,False,False,False,False),(True,True,True,False,False)])
def test_bounded_derivative_download_and_original_provenance(monkeypatch,tmp_path,oversized,available,derivative_large,success,used):
    media,body,calls=derivative_media(monkeypatch,tmp_path,oversized=oversized,available=available,derivative_large=derivative_large)
    c=candidate(title='Garden.jpg');before=c.model_dump();downloaded=media.download(c)
    assert (downloaded==body) is success and c.model_dump()==before
    assert bool(media.stats['commons_derivatives_used']) is used
    assert len(calls)==(2 if oversized and available else 1)


@pytest.mark.parametrize('host',['upload.wikimedia.org','thumb.wikimedia.org'])
def test_derivative_api_requires_actual_commons_thumb_metadata(monkeypatch,tmp_path,host):
    real_client=httpx.Client;requested=[]
    def handler(request):
        requested.append(request)
        return httpx.Response(200,json={'query':{'pages':{'1':{'title':'File:Garden.jpg','imageinfo':[{'thumburl':f'https://{host}/wikipedia/commons/thumb/a/ab/Garden.jpg/1920px-Garden.jpg','thumbwidth':1920,'thumbheight':1440}]}}}})
    monkeypatch.setattr(httpx,'Client',lambda **kw:real_client(transport=httpx.MockTransport(handler),**kw))
    client=WikimediaCommonsClient();client.cache=DiskCache('derivative-fixture');client.cache.cache_dir=tmp_path
    result=client.get_derivative_info('Garden.jpg',1920)
    assert result['width']==1920 and requested[0].url.params['iiurlheight']=='1920'
    assert client.get_derivative_info('Garden.jpg',1920)==result and len(requested)==1


def test_official_thumb_host_derivative_downloads_with_same_bounds(monkeypatch,tmp_path):
    media,body,_=derivative_media(monkeypatch,tmp_path,oversized=True)
    media.commons.get_derivative_info=lambda *args:{'url':'https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/Garden.jpg/800px-Garden.jpg','width':800,'height':600,'original_file':'Garden.jpg'}
    assert media.download(candidate(title='Garden.jpg'))==body and media.stats['commons_derivatives_used']==1


def test_cli_cold_start_has_no_pipeline_source_import_cycle():
    result=subprocess.run([sys.executable,'-c','from datafactory.cli import app'],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('untrusted_url',[False,True])
def test_derivative_wrong_dimensions_or_host_never_counts_as_recovered(monkeypatch,tmp_path,untrusted_url):
    media,_,_=derivative_media(monkeypatch,tmp_path,oversized=True)
    media.commons.get_derivative_info=lambda *args:{'url':'https://evil.example/thumb/Garden.jpg' if untrusted_url else 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Garden.jpg/900px-Garden.jpg',
        'width':900,'height':600,'original_file':'Garden.jpg'}
    assert media.download(candidate(title='Garden.jpg')) is None
    assert media.stats['commons_derivatives_used']==0


def test_commons_api_percent_and_unicode_filename_roundtrips(monkeypatch,tmp_path):
    from datafactory.utils.media_metadata import commons_file_key
    real_client=httpx.Client;name='नमस्ते A%20B; (C).jpg'
    monkeypatch.setattr(httpx,'Client',lambda **kw:real_client(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={
        'query':{'pages':{'1':{'title':'File:'+name,'imageinfo':[{'url':'https://upload.wikimedia.org/a.jpg','width':800,'height':600,'mime':'image/jpeg','extmetadata':{}}]}}}})),**kw))
    client=WikimediaCommonsClient();client.cache=DiskCache('percent-fixture');client.cache.cache_dir=tmp_path
    result=client.get_image_info(name)
    assert commons_file_key(result['source_page'])==name and '%2520' in result['source_page']


def fresh_retry(research_pack,*,changed_identity=False):
    settings,source,place,output,*_=research_pack
    previous=image_result(research_pack,local=False)
    target=source.with_name('v3-fixture-retry');shutil.copytree(source,target)
    places=json.loads((target/'places.json').read_text());places[0]['description']='Updated nonidentity metadata'
    if changed_identity:places[0]['name']='A different place'
    atomic_json(target/'places.json',places)
    handoff=export_research(target,output/'retry',settings=settings,types=['REAL_PRIMARY_IMAGE'],priorities=['P0'])
    return previous,handoff['handoff_id'],output/'retry-results.json'


def test_registered_retry_mapping_keeps_evidence_and_assigns_registered_id(research_pack):
    previous,new_id,output=fresh_retry(research_pack)
    original=json.loads(previous.read_text())
    report=build_retry_bundle(previous,new_id,output,settings=research_pack[0]);bundle=json.loads(output.read_text())
    assert report['classification']=={'RETRYABLE_WITH_EXISTING_RESEARCH':1}
    assert bundle['handoff_id']==new_id and bundle['results'][0]['sources']==original['results'][0]['sources']
    assert bundle['results'][0]['result']==original['results'][0]['result']
    assert bundle['results'][0]['task_id']==report['mapping'][0]['new_task_id']
    assert import_research(output,settings=research_pack[0])['summary']['matched']==1


def test_retry_changed_identity_does_not_reuse_and_bad_registered_types_fail(research_pack):
    previous,new_id,output=fresh_retry(research_pack,changed_identity=True)
    report=build_retry_bundle(previous,new_id,output,settings=research_pack[0])
    assert report['classification']=={'NEW_RESEARCH_REQUIRED':1}
    assert json.loads(output.read_text())['results'][0]['status']=='UNRESOLVED'
    data=json.loads(previous.read_text());data['results'][0]['type']='WEBSITE';data['results'][0]['result']={};atomic_json(previous,data)
    with pytest.raises(ValueError,match='registered task'):build_retry_bundle(previous,new_id,output.with_name('bad.json'),settings=research_pack[0])
    with pytest.raises(ValueError,match='Missing registered handoff'):build_retry_bundle(previous,'handoff_'+'0'*24,output.with_name('missing.json'),settings=research_pack[0])


@pytest.mark.parametrize('status',['PARTIAL','CONFLICT','UNRESOLVED'])
def test_retry_does_not_force_non_found_research(research_pack,status):
    previous,new_id,output=fresh_retry(research_pack)
    data=json.loads(previous.read_text());data['results'][0]['status']=status;atomic_json(previous,data)
    build_retry_bundle(previous,new_id,output,settings=research_pack[0])
    assert json.loads(output.read_text())['results'][0]['status']==status


@pytest.mark.parametrize('status,category,retryable',[(429,'AI_QUOTA_DEFERRED',True),(403,'AI_UNAVAILABLE',False),(503,'AI_UNAVAILABLE',True),(500,'AI_HTTP_ERROR',True)])
def test_provider_failure_diagnostics_never_capture_headers_or_response(monkeypatch,tmp_path,status,category,retryable):
    monkeypatch.setenv('GEMINI_API_KEY','fixture-private-key-canary')
    cfg=config();cfg.limits['max_retry_delay_seconds']=0
    provider=GeminiProvider(cfg,httpx.MockTransport(lambda request:httpx.Response(status,headers={'retry-after':'30'},text='sensitive-response-canary')))
    provider.verified=True
    router=AIRouter({},tmp_path,cfg,[provider]);result=router.analyze({'id':'poi'},'media_audit',{},[b'image'])
    diagnostic=result['provider_failures'][0]
    assert diagnostic['http_status']==status and diagnostic['status_category']==category and diagnostic['retryable'] is retryable
    assert diagnostic['rate_limited'] is (status==429)
    saved=json.dumps(router.report())+''.join(p.read_text() for p in tmp_path.rglob('*.json'))
    assert 'fixture-private-key-canary' not in saved and 'sensitive-response-canary' not in saved


def test_timeout_and_invalid_response_diagnostics(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','fixture-key')
    def timeout(request):raise httpx.ReadTimeout('sensitive url/key')
    provider=GroqProvider(config(),httpx.MockTransport(timeout))
    with pytest.raises(AIError) as exc:provider._request('GET','/models')
    assert exc.value.diagnostic('groq')['error_class']=='TimeoutException'
    provider=GroqProvider(config(),httpx.MockTransport(lambda request:httpx.Response(200,text='not JSON secret')))
    with pytest.raises(AIError) as exc:provider._request('GET','/models')
    assert exc.value.diagnostic('groq')['status_category']=='AI_RESULT_INVALID'
