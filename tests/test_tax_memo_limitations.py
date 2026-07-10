import pandas as pd

from calculations_tax_review_pack import build_tax_review_memo


def _minimal_pack_inputs():
    issue_matrix = pd.DataFrame(
        [
            {
                "세무 이슈": "보유세 부담 검토",
                "위험수준": "주의",
                "발생 근거": "회사 전체 추정값 기준",
            }
        ]
    )
    reconciliation = pd.DataFrame(
        [
            {
                "보유세 / FFO": 0.12,
                "공시가격 / 장부가액": 0.52,
                "추정 보유세(억원)": 12.5,
            }
        ]
    )
    request_list = pd.DataFrame(
        [
            {
                "요청자료": "재산세 고지서",
                "요청 목적": "추정 보유세와 실제 고지세액 대사",
            }
        ]
    )
    ffo_stress = pd.DataFrame([{"FFO 대비": 0.12}, {"FFO 대비": 0.18}])
    return issue_matrix, reconciliation, request_list, ffo_stress


def test_tax_review_memo_always_contains_limitation_wording():
    issue_matrix, reconciliation, request_list, ffo_stress = _minimal_pack_inputs()
    memo = build_tax_review_memo(
        {"company_name": "테스트리츠", "stock_code": "000000"},
        "2026년 / official_snapshot",
        issue_matrix,
        reconciliation,
        request_list,
        ffo_stress,
    )

    assert "## 5. 제한 및 유의사항" in memo
    assert "확정 세액" in memo
    assert "법률의견" in memo


def test_tax_review_memo_adds_snapshot_estimate_limitation_for_estimates():
    issue_matrix, reconciliation, request_list, ffo_stress = _minimal_pack_inputs()
    memo = build_tax_review_memo(
        {"company_name": "테스트리츠", "stock_code": "000000"},
        "2026년 / peer_snapshot_estimate / 회사 전체 Snapshot 기반 추정",
        issue_matrix,
        reconciliation,
        request_list,
        ffo_stress,
    )

    assert "Snapshot 기반 추정값" in memo
    assert "신고 목적 세액이 아니며" in memo
    assert "예비 분석 입력값" in memo
