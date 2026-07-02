"""M15 API integration tests using FastAPI TestClient."""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


CORP_PAYLOAD = {
    "ticker": "AAPL",
    "company": "Apple Inc.",
    "event_type": "earnings",
    "description": "Q4 2024 earnings beat consensus estimates by 8%.",
    "sector": "technology",
    "industry": "consumer electronics",
    "country": "US",
    "confidence": 0.92,
    "source": "sec_filing",
    "timestamp": 1700000000.0,
    "importance": "high",
    "severity": "medium",
    "metadata": {"eps_beat": 0.08},
    "tags": ["earnings", "beat"],
}

MACRO_PAYLOAD = {
    "event_type": "cpi",
    "country": "US",
    "timestamp": 1700100000.0,
    "importance": "critical",
    "description": "CPI rose 0.3% MoM vs 0.2% expected — hottest reading since March.",
    "actual": 3.4,
    "forecast": 3.2,
    "previous": 3.1,
    "metadata": {"source": "bls"},
}


@pytest.fixture(scope="module", autouse=True)
def seed_events():
    """Seed engines via API so all tests share data."""
    client.post("/events/company", json={**CORP_PAYLOAD, "ticker": "AAPL", "event_type": "earnings"})
    client.post("/events/company", json={**CORP_PAYLOAD, "ticker": "MSFT", "event_type": "dividend_increase"})
    client.post("/events/company", json={**CORP_PAYLOAD, "ticker": "JNJ", "event_type": "fda_approval",
                                         "sector": "healthcare", "description": "FDA approval for oncology drug"})
    client.post("/events/macro", json={**MACRO_PAYLOAD, "event_type": "cpi"})
    client.post("/events/macro", json={**MACRO_PAYLOAD, "event_type": "fomc",
                                        "description": "Federal Reserve raised rates 25bps"})


class TestCorporateEventsAPI:
    def test_post_corporate_event_200(self):
        r = client.post("/events/company", json=CORP_PAYLOAD)
        assert r.status_code == 200

    def test_post_corporate_event_returns_id(self):
        r = client.post("/events/company", json=CORP_PAYLOAD)
        data = r.json()
        assert "id" in data

    def test_post_corporate_stores_ticker(self):
        r = client.post("/events/company", json={**CORP_PAYLOAD, "ticker": "NVDA"})
        assert r.json()["ticker"] == "NVDA"

    def test_get_corporate_events_200(self):
        r = client.get("/events/company")
        assert r.status_code == 200

    def test_get_corporate_events_returns_list(self):
        r = client.get("/events/company")
        assert isinstance(r.json(), list)

    def test_get_corporate_events_has_items(self):
        r = client.get("/events/company")
        assert len(r.json()) > 0

    def test_get_corporate_by_id_200(self):
        ev_id = client.post("/events/company", json=CORP_PAYLOAD).json()["id"]
        r = client.get(f"/events/company/{ev_id}")
        assert r.status_code == 200

    def test_get_corporate_by_id_correct_id(self):
        ev_id = client.post("/events/company", json=CORP_PAYLOAD).json()["id"]
        r = client.get(f"/events/company/{ev_id}")
        assert r.json()["id"] == ev_id

    def test_get_corporate_by_id_404_missing(self):
        r = client.get("/events/company/nonexistent-id-xyz")
        assert r.status_code == 404

    def test_filter_by_ticker(self):
        r = client.get("/events/company?ticker=AAPL")
        data = r.json()
        assert all(ev["ticker"] == "AAPL" for ev in data)


class TestMacroEventsAPI:
    def test_post_macro_event_200(self):
        r = client.post("/events/macro", json=MACRO_PAYLOAD)
        assert r.status_code == 200

    def test_post_macro_returns_id(self):
        r = client.post("/events/macro", json=MACRO_PAYLOAD)
        assert "id" in r.json()

    def test_post_macro_surprise_computed(self):
        r = client.post("/events/macro", json=MACRO_PAYLOAD)
        data = r.json()
        assert "surprise" in data
        assert abs(data["surprise"] - (3.4 - 3.2)) < 1e-6

    def test_get_macro_events_200(self):
        r = client.get("/events/macro")
        assert r.status_code == 200

    def test_get_macro_events_returns_list(self):
        r = client.get("/events/macro")
        assert isinstance(r.json(), list)

    def test_get_macro_by_id_200(self):
        ev_id = client.post("/events/macro", json=MACRO_PAYLOAD).json()["id"]
        r = client.get(f"/events/macro/{ev_id}")
        assert r.status_code == 200

    def test_get_macro_by_id_404_missing(self):
        r = client.get("/events/macro/zzz-missing")
        assert r.status_code == 404

    def test_filter_macro_by_country(self):
        r = client.get("/events/macro?country=US")
        data = r.json()
        assert all(ev["country"] == "US" for ev in data)


class TestStatisticsAPI:
    def test_get_statistics_200(self):
        r = client.get("/events/statistics")
        assert r.status_code == 200

    def test_statistics_has_corporate(self):
        r = client.get("/events/statistics")
        assert "corporate" in r.json()

    def test_statistics_has_macro(self):
        r = client.get("/events/statistics")
        assert "macro" in r.json()

    def test_statistics_corporate_total_positive(self):
        r = client.get("/events/statistics")
        assert r.json()["corporate"]["total"] > 0


class TestTimelineAPI:
    def test_post_timeline_200(self):
        r = client.post("/events/timeline", json={"grouping": "day"})
        assert r.status_code == 200

    def test_timeline_returns_dict_or_list(self):
        r = client.post("/events/timeline", json={"grouping": "day"})
        data = r.json()
        assert isinstance(data, (dict, list))

    def test_timeline_week_grouping(self):
        r = client.post("/events/timeline", json={"grouping": "week"})
        assert r.status_code == 200

    def test_upcoming_200(self):
        r = client.get("/events/upcoming")
        assert r.status_code == 200


class TestCalendarAPI:
    def test_post_calendar_agenda_200(self):
        r = client.post("/events/calendar", json={"view": "agenda"})
        assert r.status_code == 200

    def test_get_heatmap_200(self):
        r = client.get("/events/heatmap")
        assert r.status_code == 200

    def test_heatmap_returns_list(self):
        r = client.get("/events/heatmap")
        data = r.json()
        assert isinstance(data, list)


class TestEventStudyAPI:
    def test_post_event_study_200(self):
        payload = {
            "event_id": "evt-study-001",
            "tickers": ["AAPL", "MSFT"],
            "actual_returns": {
                "AAPL": [0.001, -0.002, 0.003, 0.001, -0.001, 0.015, 0.010, 0.008, 0.005, 0.003],
                "MSFT": [0.001, -0.001, 0.002, 0.0, -0.001, 0.012, 0.008, 0.006, 0.004, 0.002],
            },
            "expected_returns": {
                "AAPL": [0.001] * 10,
                "MSFT": [0.001] * 10,
            },
            "windows": ["[-3,+3]", "[-5,+5]"],
        }
        r = client.post("/events/study", json=payload)
        assert r.status_code == 200

    def test_event_study_returns_dict_with_windows(self):
        payload = {
            "event_id": "evt-study-002",
            "tickers": ["AAPL"],
            "actual_returns": {"AAPL": [0.001] * 10},
            "expected_returns": {"AAPL": [0.001] * 10},
            "windows": ["[-1,+1]"],
        }
        r = client.post("/events/study", json=payload)
        assert r.status_code == 200


class TestEventImpactAPI:
    def test_post_impact_200(self):
        payload = {
            "event_id": "evt-impact-001",
            "ticker": "AAPL",
            "pre_returns": [0.001, -0.001, 0.002, 0.001, 0.0],
            "post_returns": [0.015, 0.010, 0.005, 0.003, -0.001],
            "market_returns": [0.001] * 10,
            "pre_volumes": [1000000, 1200000, 900000, 1100000, 1050000],
            "post_volumes": [3000000, 2500000, 1800000, 1400000, 1200000],
            "gap_return": 0.02,
            "expected_daily_return": 0.001,
            "metadata": {},
        }
        r = client.post("/events/impact", json=payload)
        assert r.status_code == 200

    def test_impact_has_post_return(self):
        payload = {
            "event_id": "evt-impact-002",
            "ticker": "MSFT",
            "pre_returns": [0.001] * 5,
            "post_returns": [0.01] * 5,
            "market_returns": [0.001] * 10,
            "pre_volumes": [1000000] * 5,
            "post_volumes": [2000000] * 5,
            "gap_return": 0.01,
            "expected_daily_return": 0.001,
            "metadata": {},
        }
        r = client.post("/events/impact", json=payload)
        assert "post_return" in r.json()


class TestCatalystAPI:
    def test_get_catalysts_200(self):
        r = client.get("/events/catalysts")
        assert r.status_code == 200

    def test_post_catalyst_score_200(self):
        ev_id = client.post("/events/company", json=CORP_PAYLOAD).json()["id"]
        r = client.post("/events/catalysts/score", json={"event_id": ev_id})
        assert r.status_code == 200


class TestIntelligenceAPI:
    def test_post_intelligence_200(self):
        ev_id = client.post("/events/company", json=CORP_PAYLOAD).json()["id"]
        r = client.post("/events/intelligence", json={"event_id": ev_id})
        assert r.status_code == 200

    def test_post_intelligence_has_bull_case(self):
        ev_id = client.post("/events/company", json=CORP_PAYLOAD).json()["id"]
        r = client.post("/events/intelligence", json={"event_id": ev_id})
        assert "bull_case" in r.json()

    def test_post_intelligence_404_missing_event(self):
        r = client.post("/events/intelligence", json={"event_id": "no-such-event"})
        assert r.status_code == 404

    def test_post_intelligence_macro_200(self):
        ev_id = client.post("/events/macro", json=MACRO_PAYLOAD).json()["id"]
        r = client.post("/events/intelligence/macro", json={"event_id": ev_id})
        assert r.status_code == 200

    def test_get_intelligence_score_200(self):
        ev_id = client.post("/events/company", json=CORP_PAYLOAD).json()["id"]
        r = client.get(f"/events/intelligence/score/{ev_id}")
        assert r.status_code == 200

    def test_intelligence_score_has_overall(self):
        ev_id = client.post("/events/company", json=CORP_PAYLOAD).json()["id"]
        r = client.get(f"/events/intelligence/score/{ev_id}")
        assert "overall_score" in r.json()


class TestClustersAPI:
    def test_get_clusters_200(self):
        r = client.get("/events/clusters")
        assert r.status_code == 200

    def test_clusters_has_distribution(self):
        r = client.get("/events/clusters")
        assert "distribution" in r.json()


class TestSearchAPI:
    def test_post_search_200(self):
        r = client.post("/events/search", json={"query": "earnings"})
        assert r.status_code == 200

    def test_search_has_hits(self):
        r = client.post("/events/search", json={"query": "earnings"})
        assert "hits" in r.json()

    def test_get_search_facets_200(self):
        r = client.get("/events/search/facets")
        assert r.status_code == 200

    def test_get_search_autocomplete_200(self):
        r = client.get("/events/search/autocomplete?q=AAPL")
        assert r.status_code == 200

    def test_autocomplete_returns_list(self):
        r = client.get("/events/search/autocomplete?q=AA")
        assert isinstance(r.json(), list)


class TestReportAPI:
    def test_post_report_daily_200(self):
        r = client.post("/events/report", json={"report_type": "daily"})
        assert r.status_code == 200

    def test_report_has_title(self):
        r = client.post("/events/report", json={"report_type": "daily"})
        assert "title" in r.json()

    def test_report_has_sections(self):
        r = client.post("/events/report", json={"report_type": "daily"})
        assert "sections" in r.json()

    def test_post_report_macro_200(self):
        r = client.post("/events/report", json={"report_type": "macro"})
        assert r.status_code == 200

    def test_post_report_catalyst_200(self):
        r = client.post("/events/report", json={"report_type": "catalyst"})
        assert r.status_code == 200

    def test_post_report_company_200(self):
        r = client.post("/events/report", json={"report_type": "company", "ticker": "AAPL"})
        assert r.status_code == 200

    def test_post_report_sector_200(self):
        r = client.post("/events/report", json={"report_type": "sector", "sector": "technology"})
        assert r.status_code == 200


class TestExportAPI:
    def test_get_export_200(self):
        r = client.get("/events/export")
        assert r.status_code == 200

    def test_export_has_events(self):
        r = client.get("/events/export")
        assert "events" in r.json()

    def test_export_has_count(self):
        r = client.get("/events/export")
        assert "count" in r.json()
