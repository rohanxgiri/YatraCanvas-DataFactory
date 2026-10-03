"""Persist an isolated synthetic research round trip, with no live sources/cloud."""
import json
import sys
import tempfile
from pathlib import Path
import pytest
from typer.testing import CliRunner
from datafactory.config.settings import get_settings
from datafactory.utils.atomic import atomic_json
from datafactory.pipeline.validate import validate_release_package
from datafactory.pipeline.usability import usability
from datafactory.research.importer import import_research
from datafactory.cli import app


def main():
    real_settings=get_settings()
    sys.path.insert(0,str(real_settings.project_root/'tests'))
    import conftest
    from test_research_handoff import research_pack, result_file, image_result, inventory
    root=Path(tempfile.mkdtemp(prefix='fixture-roundtrip-',dir=real_settings.project_root/'scratch'))
    with pytest.MonkeyPatch.context() as patch:
        sample=conftest.sample_place.__wrapped__(conftest.sample_city_metadata.__wrapped__())
        sample.id='fixture_venue'; sample.name='Synthetic Fixture Palace'; sample.alternate_names=[]
        sample.contact.website='https://fixture-venue.example'
        sample.contact.phone=None; sample.external_ids.wikidata_id=None
        setup=research_pack.__wrapped__(root,patch,conftest.sample_city_metadata.__wrapped__(),sample)
        settings,pack,place,handoff,exported,tasks=setup
        city=json.loads((pack/'city.json').read_text(encoding='utf-8'))
        before=inventory(pack); before_place=json.loads((pack/'places.json').read_text(encoding='utf-8'))[0]
        before_usability=usability([before_place],city,pack)
        hours_file=result_file(setup); hours=json.loads(hours_file.read_text(encoding='utf-8'))['results'][0]
        image_file=image_result(setup); image=json.loads(image_file.read_text(encoding='utf-8'))['results'][0]
        result={'schema_version':'1.0','handoff_id':exported['handoff_id'],'results':[hours,image]}
        atomic_json(image_file,result)
        runner=CliRunner()
        cli=runner.invoke(app,['research-import','--file',str(image_file),'--dry-run'])
        assert cli.exit_code==0,cli.output
        after_dry=inventory(pack)
        dry=import_research(image_file,settings=settings)
        assert before==after_dry and dry['summary']['matched']==2
        class FixtureRouter:
            def analyze(self,*args,**kwargs):
                return {'status':'OK','result':{'decision':'ACCEPT','confidence':.99,'identity_match':True,'identity_confidence':.99,
                    'real_photograph':True,'wrong_place_risk':.01,'landmark_prominence':.8,'mobile_card_suitability':.8,
                    'watermark_or_obstruction':False,'reason_codes':['EXPLICIT_SYNTHETIC_FIXTURE']}}
            def report(self):
                return {'AI_MODE':'FREE_ONLY','stats':{'calls':0},'fixture_router':True,'paid_providers_invoked':0,'paid_feature_calls':0}
        # Real command dispatch; dependency injection replaces cloud with a clearly
        # labelled fixture response. No source assertions are written to real packs.
        import datafactory.research.importer as module
        original=module.import_research
        def fixture_import(file,**kwargs):
            return original(file,router=FixtureRouter(),**kwargs)
        patch.setattr(module,'import_research',fixture_import)
        applied_cli=runner.invoke(app,['research-import','--file',str(image_file),'--apply'])
        assert applied_cli.exit_code==0,applied_cli.output
        history=next((settings.data_dir/'research/imports').glob('*.json'))
        applied=json.loads(history.read_text(encoding='utf-8')); output=Path(applied['output_pack'])
        validate_release_package(output)
        after_place=json.loads((output/'places.json').read_text(encoding='utf-8'))[0]
        changed=[k for k in before_place if before_place[k]!=after_place[k]]
        assert set(changed)=={'opening_hours','images'},changed
        assert before==inventory(pack)
        provenance=json.loads((output/'field_provenance.json').read_text(encoding='utf-8'))
        assert len(provenance)==2 and all(row['task_id'] in {t['task_id'] for t in tasks} for row in provenance)
        after_usability=json.loads((output/'usability.json').read_text(encoding='utf-8'))
        report={'fixture_only':True,'fixture_root':str(root),'export':exported,'dry_run':dry,'apply':applied,
            'command_exit_codes':{'research-import --dry-run':cli.exit_code,'research-import --apply':applied_cli.exit_code},
            'offline_rebuild':'Completed atomically by apply; validate_release_package passed for JSON/JSONL/Parquet/SQLite/media/checksums',
            'changed_place_fields':changed,'provenance_rows':len(provenance),'original_v3_preserved':before==inventory(pack),
            'readiness_before':{k:before_usability[k] for k in ('GENERAL_USABILITY','REAL_REQUIRED_MEDIA_COVERAGE','SOURCE_DATA_READY','critical_blockers')},
            'readiness_after':{k:after_usability[k] for k in ('GENERAL_USABILITY','REAL_REQUIRED_MEDIA_COVERAGE','SOURCE_DATA_READY','critical_blockers')},
            'live_cloud_calls':0,'real_research_results_applied':0}
    atomic_json(real_settings.reports_dir/'local_intelligence/research_roundtrip.json',report)
    (real_settings.reports_dir/'local_intelligence/research_roundtrip.md').write_text('# Isolated fixture round trip\n\nAll schedules, photographs, metadata and router decisions in this fixture are synthetic. They do not claim real venue facts or licenses. No production release was changed.\n\n```json\n'+json.dumps({k:v for k,v in report.items() if k not in ('dry_run','apply')},indent=2)+'\n```\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('dry_run','apply')},indent=2))


if __name__=='__main__':
    main()
