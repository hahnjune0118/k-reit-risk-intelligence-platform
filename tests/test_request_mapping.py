import pandas as pd

from tax_request_mapping import map_tax_issues_to_request_items


def test_high_holding_tax_to_ffo_maps_to_ffo_and_tax_bill_requests():
    issue_matrix = pd.DataFrame(
        [
            {
                "세무 이슈": "FFO proxy 현금유출 스트레스",
                "위험수준": "높음",
                "발생 근거": "보유세 / FFO proxy가 Peer 상위권",
                "영향받는 지표": "보유세 / FFO proxy",
                "검토 방향": "배당가능재원 검토",
                "데이터 기준": "peer_snapshot_estimate",
            }
        ]
    )

    requests = map_tax_issues_to_request_items(issue_matrix, "peer_snapshot_estimate", {"asset_level_tax_data_exists": False})

    assert "재산세 고지서" in requests["요청자료"].tolist()
    assert "FFO proxy 산정자료" in requests["요청자료"].tolist()
    assert requests["관련 이슈"].str.contains("FFO proxy 현금유출 스트레스", na=False).any()


def test_missing_asset_level_source_maps_to_asset_detail_requests():
    issue_matrix = pd.DataFrame(
        [
            {
                "세무 이슈": "자산별 과세자료 정합성 검토 필요",
                "위험수준": "주의",
                "발생 근거": "회사 전체 추정 행 사용",
                "영향받는 지표": "공시가격 / 장부가액",
                "검토 방향": "자산별 대사",
                "데이터 기준": "peer_snapshot_estimate",
            }
        ]
    )

    requests = map_tax_issues_to_request_items(issue_matrix, "peer_snapshot_estimate", {"asset_level_tax_data_exists": False})

    assert "자산별 장부가액 명세" in requests["요청자료"].tolist()
    assert "토지대장" in requests["요청자료"].tolist()
    assert "건축물대장" in requests["요청자료"].tolist()
    assert requests["관련 이슈"].str.contains("자산별 상세자료 부족 보완", na=False).any()


def test_data_insufficient_still_returns_actionable_requests():
    requests = map_tax_issues_to_request_items(pd.DataFrame(), "data_insufficient", {})

    assert not requests.empty
    assert "원천자료 목록" in requests["요청자료"].tolist()
    assert requests["source trigger"].str.contains("data_insufficient", na=False).any()
