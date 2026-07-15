from data_source_policy import (
    SOURCE_POLICIES,
    contains_estimate_source,
    dominant_source_type,
    get_source_policy,
    source_policy_table,
)


def test_source_policy_has_required_canonical_types():
    expected = {
        "official_disclosure",
        "api_snapshot",
        "peer_snapshot",
        "peer_snapshot_estimate",
        "sample_estimate",
        "data_insufficient",
    }

    assert expected.issubset(SOURCE_POLICIES)
    table = source_policy_table()
    assert expected.issubset(set(table["source_type"]))
    assert {"한국어 라벨", "신뢰수준", "허용 산출물", "Memo 한계 문구", "UI 경고 문구"}.issubset(table.columns)


def test_source_policy_aliases_and_estimate_detection_are_safe():
    assert dominant_source_type("sample_snapshot") == "sample_estimate"
    assert dominant_source_type("peer_snapshot_estimate, sample_snapshot") == "peer_snapshot_estimate"
    assert dominant_source_type("data_missing") == "data_insufficient"
    assert get_source_policy("investment_property_estimate").source_type == "peer_snapshot_estimate"
    assert contains_estimate_source("peer_snapshot_estimate")
    assert contains_estimate_source("회사 전체 Snapshot 기반 추정")
