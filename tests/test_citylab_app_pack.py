import json
import sqlite3
import zipfile
from pathlib import Path

import pytest
from test_research_handoff import research_pack, inventory
from datafactory.research.export import snapshot
from datafactory.citylab_patch import import_citylab_patch
from datafactory.app_pack import export_app_pack, validate_app_pack
from datafactory.utils.hashing import compute_sha256


def patch(fixture, tmp_path, edits=None, *, operation='UPDATE', pid=None, before=None):
    settings, source, place, *_ = fixture
    changes = [{'place_id':pid or place['id'], 'operation':operation,
                'changes':edits or {'description':'Human correction fixture'},
                'before':before if before is not None else {'description':place['description']}, 'author':'QA fixture'}]
    data = json.dumps(changes).encode()
    import hashlib
    manifest = {'patch_schema_version':1,'patch_id':'citylab-test','city_id':place['city']['id'],
                'city_name':place['city']['name'],'state':place['city']['state'],'country':place['city']['country'],
                'source_pack_version':source.name,'source_pack_fingerprint':snapshot(source),'change_count':1,
                'media_count':0,'checksums':{'changes.json':hashlib.sha256(data).hexdigest()}}
    output = tmp_path / 'repair.zip'
    with zipfile.ZipFile(output,'w') as archive:
        archive.writestr('manifest.json',json.dumps(manifest))
        archive.writestr('changes.json',data)
    return output


def test_patch_dry_run_apply_immutable_and_stale(research_pack, tmp_path):
    settings, source, place, *_ = research_pack
    bundle = patch(research_pack,tmp_path)
    before = inventory(source)
    assert import_citylab_patch(bundle,settings=settings)['summary'] == {'APPLY':1}
    result = import_citylab_patch(bundle,settings=settings,apply=True,output_version='v4-citylab-test')
    assert inventory(source) == before
    new = Path(result['output_pack'])
    assert json.loads((new/'places.json').read_text())[0]['description']=='Human correction fixture'
    assert import_citylab_patch(bundle,settings=settings)['summary'] == {'REVIEW':1}
    with pytest.raises(ValueError):
        import_citylab_patch(bundle,settings=settings,apply=True,output_version='v4-citylab-test')


@pytest.mark.parametrize('field,value', [('latitude',91),('longitude',float('nan')),('opening_hours',{'raw':'invented hours','verified':False}),('name','')])
def test_invalid_repairs_rejected(research_pack,tmp_path,field,value):
    from datafactory.citylab_patch import get_value
    bundle=patch(research_pack,tmp_path,{field:value},before={field:get_value(research_pack[2],field)})
    assert import_citylab_patch(bundle,settings=research_pack[0])['summary']=={'REJECT':1}


def test_zip_traversal_rejected(research_pack,tmp_path):
    bundle=patch(research_pack,tmp_path)
    with zipfile.ZipFile(bundle,'a') as archive:
        archive.writestr('../escape','bad')
    with pytest.raises(ValueError, match='escapes'):
        import_citylab_patch(bundle,settings=research_pack[0])


def test_app_pack_queries_integrity_and_no_source_mutation(research_pack,tmp_path):
    settings,source,place,*_=research_pack
    before=inventory(source)
    out=tmp_path/'app-runtime'
    assert export_app_pack('Jaipur',settings=settings,output=out,dry_run=True)['dry_run']
    assert not out.exists()
    report=export_app_pack('Jaipur',settings=settings,output=out)
    assert inventory(source)==before
    assert report['place_count']==1
    validate_app_pack(out)
    with sqlite3.connect(out/'city_pack.sqlite') as db:
        assert db.execute('SELECT id FROM places').fetchone()[0]==place['id']
        assert db.execute('SELECT count(*) FROM place_search WHERE place_search MATCH ?',('Hawa',)).fetchone()[0]==1
    with (out/'city_pack.sqlite').open('ab') as handle:
        handle.write(b'corrupt')
    with pytest.raises(ValueError, match='checksum'):
        validate_app_pack(out)


def attach_media(bundle, content):
    import hashlib
    with zipfile.ZipFile(bundle) as archive:
        files = {name:archive.read(name) for name in archive.namelist()}
    manifest=json.loads(files['manifest.json'])
    files['media/photo.png']=content
    manifest['media_count']=1
    manifest['checksums']['media/photo.png']=hashlib.sha256(content).hexdigest()
    files['manifest.json']=json.dumps(manifest).encode()
    with zipfile.ZipFile(bundle,'w') as archive:
        for name,data in files.items():archive.writestr(name,data)


def test_test_media_requires_optin_and_never_enters_strict_projection(research_pack,tmp_path):
    from test_local_intelligence import photo
    from datafactory.citylab_patch import get_value
    media={'file':'media/photo.png','media_class':'TEST_ONLY_REAL','source':'Fixture photograph',
           'identity_confirmed':True,'real_photograph_confirmed':True,'original_filename':'fixture.png'}
    bundle=patch(research_pack,tmp_path,{'media':media},before={'media':get_value(research_pack[2],'media')})
    attach_media(bundle,photo())
    settings=research_pack[0]
    assert import_citylab_patch(bundle,settings=settings)['summary']=={'REVIEW':1}
    assert import_citylab_patch(bundle,settings=settings,allow_test_media=True)['summary']=={'APPLY':1}
    result=import_citylab_patch(bundle,settings=settings,apply=True,allow_test_media=True,output_version='v4-photo-test')
    new=Path(result['output_pack'])
    row=json.loads((new/'places.json').read_text())[0]
    assert row['images']['primary'] is None
    test_record=json.loads((new/'test_media_manifest.json').read_text())['records'][row['id']]
    assert not test_record['counts_toward_source_readiness']
    assert test_record['image']['license']=='UNVERIFIED_TEST_ONLY'
    assert export_app_pack('Jaipur',settings=settings)['media_count']==0
    assert export_app_pack('Jaipur',settings=settings,allow_test_media=True)['media_count']==1


def test_undecodable_media_rejected(research_pack,tmp_path):
    from datafactory.citylab_patch import get_value
    bundle=patch(research_pack,tmp_path,{'media':{'file':'media/photo.png','media_class':'TEST_ONLY_REAL','identity_confirmed':True,'real_photograph_confirmed':True}},before={'media':get_value(research_pack[2],'media')})
    attach_media(bundle,b'not an image')
    assert import_citylab_patch(bundle,settings=research_pack[0],allow_test_media=True)['summary']=={'REJECT':1}


def test_patch_checksum_tampering_rejected(research_pack,tmp_path):
    bundle=patch(research_pack,tmp_path)
    with zipfile.ZipFile(bundle) as archive:
        files={name:archive.read(name) for name in archive.namelist()}
    files['changes.json']=files['changes.json'].replace(b'Human correction',b'Stale correction')
    with zipfile.ZipFile(bundle,'w') as archive:
        for name,data in files.items():archive.writestr(name,data)
    with pytest.raises(ValueError,match='checksum'):
        import_citylab_patch(bundle,settings=research_pack[0])


def test_new_place_stable_id_validated_and_added(research_pack,tmp_path):
    from datafactory.utils.hashing import generate_canonical_place_id
    settings,source,place,*_=research_pack
    city=place['city'];name='Fixture Garden Entrance'
    pid=generate_canonical_place_id(city['country'],city['state'],city['name'],name)
    edits={'name':name,'category':'heritage','latitude':place['location']['latitude'],'longitude':place['location']['longitude'],'description':'Synthetic regression fixture'}
    bundle=patch(research_pack,tmp_path,edits,operation='ADD',pid=pid,before={})
    assert import_citylab_patch(bundle,settings=settings)['summary']=={'APPLY':1}
    result=import_citylab_patch(bundle,settings=settings,apply=True,output_version='v4-added-test')
    rows=json.loads((Path(result['output_pack'])/'places.json').read_text())
    assert len(rows)==2 and any(row['id']==pid for row in rows)


def test_addition_alias_duplicate_requires_review(research_pack,tmp_path):
    from datafactory.utils.hashing import generate_canonical_place_id
    settings,source,place,*_=research_pack
    city=place['city'];name='Different Entry Name'
    pid=generate_canonical_place_id(city['country'],city['state'],city['name'],name)
    edits={'name':name,'aliases':[place['name']],'category':'heritage','latitude':place['location']['latitude'],'longitude':place['location']['longitude']}
    bundle=patch(research_pack,tmp_path,edits,operation='ADD',pid=pid,before={})
    assert import_citylab_patch(bundle,settings=settings)['summary']=={'REVIEW':1}


def test_wrong_city_patch_rejected_without_source_mutation(research_pack,tmp_path):
    bundle = patch(research_pack,tmp_path)
    before = inventory(research_pack[1])
    with zipfile.ZipFile(bundle) as archive:
        files = {name:archive.read(name) for name in archive.namelist()}
    manifest = json.loads(files['manifest.json'])
    manifest['city_id'] = 'different-city'
    files['manifest.json'] = json.dumps(manifest).encode()
    with zipfile.ZipFile(bundle,'w') as archive:
        for name,data in files.items(): archive.writestr(name,data)
    with pytest.raises(ValueError,match='Wrong patch city'):
        import_citylab_patch(bundle,settings=research_pack[0])
    assert inventory(research_pack[1]) == before


def test_verified_split_hours_repair_reaches_runtime_projection(research_pack,tmp_path):
    from datafactory.citylab_patch import get_value
    hours = {'raw':'Mo-Su 11:00-14:00,17:00-22:00','source':'Synthetic verified-hours regression','verified':True,'confidence':1.0}
    bundle = patch(research_pack,tmp_path,{'opening_hours':hours},before={'opening_hours':get_value(research_pack[2],'opening_hours')})
    settings = research_pack[0]
    assert import_citylab_patch(bundle,settings=settings)['summary'] == {'APPLY':1}
    import_citylab_patch(bundle,settings=settings,apply=True,output_version='v4-hours-regression')
    output = tmp_path/'runtime-hours'
    report = export_app_pack('Jaipur',settings=settings,output=output)
    assert report['opening_hours_count'] == 1 and report['verified_hours_count'] == 1
    with sqlite3.connect(output/'city_pack.sqlite') as db:
        row = db.execute('SELECT opening_hours,opening_hours_status FROM places').fetchone()
        assert row == (hours['raw'],'VERIFIED')
