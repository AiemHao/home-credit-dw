"""Web API on the fixture warehouse: every endpoint answers, filters slice, names are whitelisted."""
import pytest
from fastapi.testclient import TestClient

from hcdw.api.app import create_app
from hcdw.api.queries import Queries
from tests.conftest import N_CUSTOMERS


@pytest.fixture(scope="module")
def client(built):
    with TestClient(create_app(dw_path=built[0])) as c:
        yield c


def test_meta_lists_dimensions_and_members(client):
    meta = client.get("/api/meta").json()
    assert {"age_bucket", "income_type"} <= {d["key"] for d in meta["dimensions"]}
    assert meta["members"]["age_bucket"][0] == "18-24"  # ordered buckets, not alphabetical
    assert any(t["table_name"] == "fact_loan_application" for t in meta["warehouse"]["tables"])


def test_kpis_and_filters_slice(client):
    total = client.get("/api/kpis").json()
    assert total["n_applications"] == N_CUSTOMERS
    member = client.get("/api/meta").json()["members"]["gender"][0]
    sliced = client.get("/api/kpis", params={"gender": member}).json()
    assert 0 < sliced["n_applications"] < N_CUSTOMERS


def test_group_by_sums_back_to_total(client):
    rows = client.get("/api/by/age_bucket").json()
    assert sum(r["n_applications"] for r in rows) == N_CUSTOMERS


@pytest.mark.parametrize("url", [
    "/api/cross?x=bureau_active_bucket&y=max_dpd_bucket",
    "/api/score-curve",
    "/api/dti-by-outcome",
    "/api/hierarchy?levels=age_bucket,income_bracket",
    "/api/bureau/kpis",
    "/api/bureau/trend?grain=year",
    "/api/bureau/by-type",
    "/api/simulator/options",
])
def test_endpoints_answer(client, url):
    assert client.get(url).status_code == 200


def test_pivot_is_a_cube_with_totals(client):
    p = client.get("/api/pivot", params={"row": "age_bucket", "col": "gender", "measure": "n_applications"}).json()
    assert p["rows"][-1] == "ALL" and p["cols"][-1] == "ALL"
    grand = next(c for c in p["cells"] if c["row_member"] == "ALL" and c["col_member"] == "ALL")
    assert grand["value"] == N_CUSTOMERS
    assert "GROUP BY CUBE" in p["sql"]


def test_saved_olap_queries_run(client):
    names = [q["name"] for q in client.get("/api/olap").json()]
    assert names == Queries.olap_files() and len(names) >= 6
    for n in names:
        assert client.get(f"/api/olap/{n}").status_code == 200


@pytest.mark.parametrize("url", [
    "/api/by/drop_table",                      # unknown dimension in the path
    "/api/kpis?bogus=1",                       # unknown filter
    "/api/pivot?row=gender&col=gender",        # same dimension twice
    "/api/pivot?row=gender&col=age_bucket&measure=evil",
    "/api/olap/..%2F..%2Fpyproject.toml",      # path traversal attempt
])
def test_bad_names_are_rejected(client, url):
    assert client.get(url).status_code in (400, 404)


def test_simulator_rules_without_model(client):
    r = client.post("/api/simulator/score",
                    json={"amt_income": 100000, "amt_annuity": 50000, "max_dpd_days": 120}).json()
    assert r["flag"] == "RED"
    assert any("90 days" in reason for reason in r["reasons"])
    ok = client.post("/api/simulator/score", json={}).json()
    assert ok["flag"] in {"GREEN", "YELLOW"}
