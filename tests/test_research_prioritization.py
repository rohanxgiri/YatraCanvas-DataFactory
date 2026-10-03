import copy
import json
import pytest
from datafactory.research.worthiness import research_worthiness
from datafactory.research.export import export_research


@pytest.mark.parametrize("tier,category,sub,kind,priority,worth", [
    ("core_destination","heritage","gate","REAL_PRIMARY_IMAGE","P0","RESEARCH_REQUIRED"),
    ("recommended","park","urban_park","REAL_PRIMARY_IMAGE","P3","RESEARCH_RECOMMENDED"),
    ("discovery","cafe","coffee_shop","REAL_PRIMARY_IMAGE","NO_RESEARCH","DO_NOT_RESEARCH"),
    ("core_destination","museum","history_museum","OPENING_HOURS","P2","RESEARCH_RECOMMENDED"),
    ("core_destination","cafe","coffee_shop","OPENING_HOURS","P2","RESEARCH_RECOMMENDED"),
    ("recommended","religious","hindu_temple","OPENING_HOURS","P3","RESEARCH_RECOMMENDED"),
    ("discovery","cafe","coffee_shop","OPENING_HOURS","P4","OPTIONAL_DEFER"),
    ("recommended","park","urban_park","OPENING_HOURS","NO_RESEARCH","DO_NOT_RESEARCH"),
    ("support","transport",None,"DESCRIPTION","NO_RESEARCH","DO_NOT_RESEARCH"),
    ("discovery","shopping",None,"DESCRIPTION","P4","OPTIONAL_DEFER"),
    ("core_destination","heritage","palace","DESCRIPTION","P2","RESEARCH_RECOMMENDED"),
    ("core_destination","heritage","palace","WEBSITE","P2","RESEARCH_RECOMMENDED"),
    ("core_destination","heritage","gate","WEBSITE","P4","OPTIONAL_DEFER"),
    ("core_destination","heritage","gate","IDENTITY_RESEARCH","P0","RESEARCH_REQUIRED"),
])
def test_field_specific_research_value(tier, category, sub, kind, priority, worth):
    place = {"tier":tier,"classification":{"category":category,"subcategory":sub},"name":"Fixture Place"}
    value = research_worthiness(place, kind)
    assert value["priority"] == priority and value["research_worthiness"] == worth
    assert value["reason_codes"]


def test_named_core_venue_hours_and_prominent_preferred_photo():
    place={"tier":"core_destination","name":"Fixture Museum","classification":{"category":"heritage","subcategory":"attraction"}}
    assert research_worthiness(place,"OPENING_HOURS")["priority"] == "P2"
    place.update(tier="recommended",prominence_score=.9,travel_relevance_score=.9)
    assert research_worthiness(place,"REAL_PRIMARY_IMAGE")["priority"] == "P1"


def test_default_optional_filters_limit_and_stable_ids(research_pack):
    settings, pack, place, output, *_ = research_pack
    # Use the shared explicit synthetic release fixture, never production data.
    clone=copy.deepcopy(place)
    clone.update(id="fixture_ordinary_cafe", name="Fixture Cafe",tier="discovery")
    clone["classification"]={"category":"cafe","subcategory":"coffee_shop"}
    clone["contact"]["website"]=None
    from datafactory.utils.atomic import atomic_json
    atomic_json(pack/"places.json",[place,clone])
    default=export_research(pack,output/"default",settings=settings)
    tasks=json.loads((output/"default/research_handoff.json").read_text())["tasks"]
    assert all(t["priority"] in {"P0","P1","P2"} and t["why_research"] for t in tasks)
    all_report=export_research(pack,output/"all",settings=settings,all_tasks=True)
    all_tasks=json.loads((output/"all/research_handoff.json").read_text())["tasks"]
    assert all_report["total"]>default["total"]
    assert any(t["priority"]=="P4" for t in all_tasks)
    assert not any(t["place_id"]==clone["id"] and t["type"]=="REAL_PRIMARY_IMAGE" for t in all_tasks)
    limited=export_research(pack,output/"limited",settings=settings,limit=1)
    first=json.loads((output/"limited/research_handoff.json").read_text())["tasks"][0]
    assert first["task_id"]==tasks[0]["task_id"] and first["priority"]=="P0"
    assert limited["remaining_in_filter"]==default["total"]-1
    hours=export_research(pack,output/"hours",settings=settings,types=["OPENING_HOURS"],priorities=["P2"])
    assert hours["total"]==1 and hours["by_type"]["OPENING_HOURS"]==1
    inventory=json.loads((output/"default/research_inventory.json").read_text())["tasks"]
    assert any(t["research_worthiness"]=="DO_NOT_RESEARCH" and t["why_not_research"] for t in inventory)
    with pytest.raises(ValueError,match="positive"):
        export_research(pack,output/"bad",settings=settings,limit=0)


# Reuse fixture definition without duplicating the export/import setup.
from test_research_handoff import research_pack
