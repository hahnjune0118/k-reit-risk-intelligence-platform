import pandas as pd

from data_source_policy import contains_estimate_source, get_source_policy
from formatting import _is_na
from red_flag_engine import risk_level_to_korean_label
from tax_request_mapping import map_tax_issues_to_request_items


RISK_ORDER = {"높음": 0, "주의": 1, "데이터 부족": 2, "정상": 3}


def _fmt_pct(value, decimals: int = 1) -> str:
    if _is_na(value):
        return "데이터 부족"
    return f"{float(value):.{decimals}f}%"


def _fmt_ratio_pct(value, decimals: int = 1) -> str:
    if _is_na(value):
        return "데이터 부족"
    return f"{float(value) * 100:.{decimals}f}%"


def _fmt_eok(value, decimals: int = 1) -> str:
    if _is_na(value):
        return "데이터 부족"
    return f"{float(value):,.{decimals}f}억원"


def _risk_label_from_ratio(value, yellow: float, red: float) -> str:
    if _is_na(value):
        return "데이터 부족"
    if float(value) >= red:
        return "높음"
    if float(value) >= yellow:
        return "주의"
    return "정상"


def build_holding_tax_reconciliation(tax_history: pd.DataFrame, latest_kpi: pd.Series | None = None) -> pd.DataFrame:
    if tax_history is None or tax_history.empty:
        return pd.DataFrame()
    latest_year = int(tax_history["year"].max())
    latest = tax_history[tax_history["year"] == latest_year].copy()
    kpi = latest_kpi if latest_kpi is not None else pd.Series(dtype="object")
    ffo = pd.to_numeric(pd.Series([kpi.get("ffo_mn_krw", pd.NA)]), errors="coerce").iloc[0]

    rows = []
    for _, row in latest.iterrows():
        book_value = row.get("book_value_mn_krw", row.get("appraised_value_mn_krw_20251231", pd.NA))
        official_price = row.get("official_price_mn_krw", row.get("토지_시가표준액_백만원", pd.NA))
        ratio = official_price / book_value if pd.notna(official_price) and pd.notna(book_value) and book_value else pd.NA
        holding_tax = row.get("보유세_추정_백만원", pd.NA)
        tax_to_ffo = holding_tax / ffo if pd.notna(holding_tax) and pd.notna(ffo) and ffo else pd.NA
        growth = row.get("보유세_5년누적증가_%", row.get("official_price_growth_5y", pd.NA))
        review_needed = "필요" if (
            (pd.notna(ratio) and (ratio < 0.35 or ratio > 0.75))
            or (pd.notna(tax_to_ffo) and tax_to_ffo >= 0.25)
            or (pd.notna(growth) and float(growth) >= 10)
        ) else "낮음"
        rows.append(
            {
                "자산명": row.get("asset_name", ""),
                "지역": row.get("location", ""),
                "장부가액(억원)": book_value / 100 if pd.notna(book_value) else pd.NA,
                "공시가격(억원)": official_price / 100 if pd.notna(official_price) else pd.NA,
                "공시가격 / 장부가액": ratio,
                "추정 과세표준(억원)": row.get("토지_과세표준_백만원", pd.NA) / 100 if pd.notna(row.get("토지_과세표준_백만원", pd.NA)) else pd.NA,
                "추정 보유세(억원)": holding_tax / 100 if pd.notna(holding_tax) else pd.NA,
                "보유세 / FFO": tax_to_ffo,
                "최근 5년 공시가격 증가율": growth / 100 if pd.notna(growth) and abs(float(growth)) > 1 else growth,
                "검토 필요 여부": review_needed,
                "source_type": row.get("source_type", row.get("official_price_source", "")),
                "source_note": row.get("source_note", ""),
            }
        )
    return pd.DataFrame(rows)


def build_source_detail(tax_history: pd.DataFrame) -> pd.DataFrame:
    if tax_history is None or tax_history.empty:
        return pd.DataFrame()
    latest_year = int(tax_history["year"].max())
    latest = tax_history[tax_history["year"] == latest_year].copy()
    rows = []
    for _, row in latest.iterrows():
        source_type = row.get("source_type", row.get("official_price_source", ""))
        policy = get_source_policy(source_type)
        rows.append(
            {
                "자산명": row.get("asset_name", ""),
                "기준연도": latest_year,
                "source_type": source_type,
                "source_label": policy.korean_label,
                "신뢰수준": policy.reliability_level,
                "source_note": row.get("source_note", row.get("official_price_source", "")),
                "식별자/주소": row.get("location", ""),
                "비고": policy.ui_warning_text,
            }
        )
    return pd.DataFrame(rows)


def build_ffo_cash_outflow_stress(
    latest_kpi: pd.Series,
    annual_summary: pd.DataFrame,
    holding_tax_increase_pct: float,
    ffo_stress_pct: float,
) -> pd.DataFrame:
    if annual_summary is None or annual_summary.empty:
        return pd.DataFrame()
    latest_year = int(annual_summary["year"].max())
    latest_tax = annual_summary.loc[annual_summary["year"] == latest_year, "보유세_추정_백만원"].iloc[0]
    base_ffo = pd.to_numeric(pd.Series([latest_kpi.get("ffo_mn_krw", pd.NA)]), errors="coerce").iloc[0]
    stressed_tax = latest_tax * (1 + holding_tax_increase_pct / 100) if pd.notna(latest_tax) else pd.NA
    stressed_ffo = base_ffo * (1 - ffo_stress_pct / 100) if pd.notna(base_ffo) else pd.NA
    incremental = stressed_tax - latest_tax if pd.notna(stressed_tax) and pd.notna(latest_tax) else pd.NA
    stressed_ratio = stressed_tax / stressed_ffo if pd.notna(stressed_tax) and pd.notna(stressed_ffo) and stressed_ffo else pd.NA
    return pd.DataFrame(
        [
            {
                "항목": "기준 보유세",
                "금액(억원)": latest_tax / 100 if pd.notna(latest_tax) else pd.NA,
                "FFO 대비": latest_tax / base_ffo if pd.notna(latest_tax) and pd.notna(base_ffo) and base_ffo else pd.NA,
                "주요 해석": "현재 Snapshot 또는 예시 데이터 기준 보유세 부담입니다.",
            },
            {
                "항목": f"보유세 +{holding_tax_increase_pct:.0f}%",
                "금액(억원)": stressed_tax / 100 if pd.notna(stressed_tax) else pd.NA,
                "FFO 대비": stressed_ratio,
                "주요 해석": f"FFO {ffo_stress_pct:.0f}% 하락과 보유세 증가를 동시에 반영한 스트레스입니다.",
            },
            {
                "항목": "추가 현금유출",
                "금액(억원)": incremental / 100 if pd.notna(incremental) else pd.NA,
                "FFO 대비": incremental / stressed_ffo if pd.notna(incremental) and pd.notna(stressed_ffo) and stressed_ffo else pd.NA,
                "주요 해석": "예산, 배당가능재원, 자금계획 검토 시 별도 설명이 필요한 증가분입니다.",
            },
        ]
    )


def build_tax_issue_matrix(
    flags: list[dict],
    reconciliation: pd.DataFrame,
    ffo_stress: pd.DataFrame,
    data_basis: str,
) -> pd.DataFrame:
    rows = []
    for flag in flags:
        level = risk_level_to_korean_label(flag.get("risk_level", "gray"))
        rows.append(
            {
                "세무 이슈": flag.get("label", ""),
                "위험수준": level,
                "발생 근거": flag.get("explanation_ko", "데이터 부족"),
                "영향받는 지표": flag.get("metric", ""),
                "검토 방향": " / ".join(flag.get("tax_review_points", []) or ["원자료 확인"]),
                "요청자료": " / ".join(flag.get("evidence_request", []) or ["관련 원천자료"]),
                "업무유형": "Tax Red Flag",
                "데이터 기준": data_basis,
            }
        )

    if reconciliation is not None and not reconciliation.empty:
        review_count = int((reconciliation["검토 필요 여부"] == "필요").sum())
        rows.append(
            {
                "세무 이슈": "자산별 과세자료 정합성 검토 필요",
                "위험수준": "주의" if review_count else "정상",
                "발생 근거": f"정합성 검토 필요 행 {review_count}건",
                "영향받는 지표": "공시가격 / 장부가액, 추정 과세표준",
                "검토 방향": "장부가액, 공시가격, 과세표준, 고지세액의 자산별 대사",
                "요청자료": "재산세 고지서 / 토지대장 / 건축물대장 / 자산별 장부가액 명세",
                "업무유형": "보유세 정합성",
                "데이터 기준": data_basis,
            }
        )

    if ffo_stress is not None and not ffo_stress.empty:
        stress_ratio = ffo_stress.loc[ffo_stress["항목"].str.contains("보유세 \\+", regex=True), "FFO 대비"]
        risk_level = _risk_label_from_ratio(stress_ratio.iloc[0] if not stress_ratio.empty else pd.NA, 0.20, 0.35)
        rows.append(
            {
                "세무 이슈": "FFO 현금유출 스트레스",
                "위험수준": risk_level,
                "발생 근거": "보유세 증가 및 FFO 하락 가정을 함께 반영",
                "영향받는 지표": "보유세 / FFO, 추가 현금유출",
                "검토 방향": "배당가능재원, 예산, 투자자 커뮤니케이션 영향 검토",
                "요청자료": "FFO 산정자료 / 배당계획 / 보유세 예산 / 공시가격 변동 분석",
                "업무유형": "현금흐름 스트레스",
                "데이터 기준": data_basis,
            }
        )

    matrix = pd.DataFrame(rows)
    if matrix.empty:
        return matrix
    return matrix.sort_values("위험수준", key=lambda s: s.map(RISK_ORDER).fillna(9)).reset_index(drop=True)


def build_tax_request_list(
    issue_matrix: pd.DataFrame,
    source_type: str | None = None,
    data_availability: dict | None = None,
) -> pd.DataFrame:
    return map_tax_issues_to_request_items(issue_matrix, source_type, data_availability)


def build_tax_automation_summary(
    issue_matrix: pd.DataFrame,
    request_list: pd.DataFrame,
    reconciliation: pd.DataFrame,
    memo_available: bool = True,
) -> pd.DataFrame:
    high_count = int(issue_matrix["위험수준"].isin(["높음"]).sum()) if issue_matrix is not None and not issue_matrix.empty else 0
    warning_count = int(issue_matrix["위험수준"].isin(["주의"]).sum()) if issue_matrix is not None and not issue_matrix.empty else 0
    request_count = len(request_list) if request_list is not None else 0
    review_needed = int((reconciliation["검토 필요 여부"] == "필요").sum()) if reconciliation is not None and not reconciliation.empty else 0
    return pd.DataFrame(
        [
            {"항목": "자동 식별된 세무 이슈", "상태": f"높음 {high_count}건 / 주의 {warning_count}건", "비고": "Tax Issue Matrix 기준"},
            {"항목": "요청자료 항목 수", "상태": f"{request_count}건", "비고": "우선순위와 요청 목적 자동 부여"},
            {"항목": "보유세 정합성 검토 상태", "상태": f"검토 필요 {review_needed}건", "비고": "공시가격·장부가액·과세표준 대사"},
            {"항목": "Tax Review Memo 생성", "상태": "가능" if memo_available else "데이터 부족", "비고": "Markdown 초안 다운로드 가능"},
        ]
    )


def _memo_source_summary(data_basis: str, source_summary: dict | None) -> dict:
    if source_summary:
        return source_summary
    policy = get_source_policy(data_basis)
    return {
        "source_type": policy.source_type,
        "source_note": str(data_basis),
        "scope_label": "Snapshot 기반 예비 분석" if contains_estimate_source(data_basis) else "공개자료 기반 예비 분석",
        "latest_year": None,
        "korean_label": policy.korean_label,
        "reliability_level": policy.reliability_level,
        "memo_limitation_text": policy.memo_limitation_text,
    }


def _lines_from_issue_matrix(issue_matrix: pd.DataFrame) -> str:
    if issue_matrix is None or issue_matrix.empty:
        return "- 현재 자동 식별된 높음/주의 항목은 제한적입니다. 원자료 대사 후 판단이 필요합니다."
    high_or_warning = issue_matrix[issue_matrix["위험수준"].isin(["높음", "주의"])] if "위험수준" in issue_matrix.columns else issue_matrix
    if high_or_warning.empty:
        high_or_warning = issue_matrix
    return "\n".join(
        f"- {row['세무 이슈']}: {row['위험수준']} - {row['발생 근거']}"
        for _, row in high_or_warning.head(6).iterrows()
    )


def _lines_from_request_list(request_list: pd.DataFrame) -> str:
    if request_list is None or request_list.empty:
        return "- 재산세 고지서, 자산별 장부가액 명세, 공시가격 조회자료를 우선 확보해야 합니다."
    return "\n".join(
        f"- {row['요청자료']}: {row['요청 목적']} ({row.get('우선순위', '중간')})"
        for _, row in request_list.head(10).iterrows()
    )


def build_tax_review_memo(
    company_profile: dict,
    data_basis: str,
    issue_matrix: pd.DataFrame,
    reconciliation: pd.DataFrame,
    request_list: pd.DataFrame,
    ffo_stress: pd.DataFrame,
    peer_summary: dict | None = None,
    source_summary: dict | None = None,
    bridge: pd.DataFrame | None = None,
    validation: dict | None = None,
) -> str:
    company_name = company_profile.get("company_name", "선택 리츠")
    stock_code = company_profile.get("stock_code", "")
    peer_summary = peer_summary or {}
    source = _memo_source_summary(data_basis, source_summary)
    source_type = source.get("source_type", "data_insufficient")
    policy = get_source_policy(source_type)
    estimated_scope = contains_estimate_source(source_type) or contains_estimate_source(data_basis) or bool(source.get("is_estimated"))
    validation = validation or {}

    recon_latest = reconciliation.iloc[0] if reconciliation is not None and not reconciliation.empty else pd.Series(dtype="object")
    stress_row = ffo_stress.iloc[1] if ffo_stress is not None and len(ffo_stress) > 1 else pd.Series(dtype="object")
    bridge_row = bridge.iloc[0] if bridge is not None and not bridge.empty else pd.Series(dtype="object")

    estimated_tax = bridge_row.get("추정 보유세(억원)", recon_latest.get("추정 보유세(억원)", pd.NA))
    tax_to_ffo = bridge_row.get("FFO 대비", recon_latest.get("보유세 / FFO", pd.NA))
    tax_to_revenue = bridge_row.get("영업수익 대비", pd.NA)
    book_price_ratio = recon_latest.get("공시가격 / 장부가액", pd.NA)
    peer_position = bridge_row.get("Peer 대비 위치", "Peer Snapshot 기준 위치 확인 필요")
    source_limit = source.get("memo_limitation_text") or policy.memo_limitation_text
    estimate_limitation = (
        "\n- 회사 전체 Snapshot 기반 추정값을 사용했습니다. 이 값은 신고 목적 세액이 아니며 Tax Review Pack 생성을 위한 예비 분석 입력값입니다."
        if estimated_scope
        else ""
    )

    missing_text = ", ".join(validation.get("missing_fields", [])) if validation.get("missing_fields") else "현재 표준 입력값 기준 중대 결측 없음"
    warning_text = "; ".join(validation.get("warnings", [])) if validation.get("warnings") else "원자료 확인 전까지 예비 분석으로 표시"

    return f"""# Tax Review Memo 초안

## 1. 검토 대상
- 회사명: {company_name}
- 종목코드: {stock_code}
- 기준연도: {source.get('latest_year') or '연도 미확인'}
- 분석 범위: {source.get('scope_label', '공개자료 기반 예비 분석')}
- source_type: {source_type}
- source_note: {source.get('source_note', data_basis)}
- source 신뢰수준: {source.get('reliability_level', policy.reliability_level)} / {source.get('korean_label', policy.korean_label)}

## 2. 핵심 수치 요약
- 추정 보유세: {_fmt_eok(estimated_tax)}
- 보유세 / FFO: {_fmt_ratio_pct(tax_to_ffo)}
- 보유세 / 영업수익: {_fmt_ratio_pct(tax_to_revenue)}
- 공시가격 / 투자부동산 장부금액: {_fmt_ratio_pct(book_price_ratio)}
- Peer 대비 위치: {peer_position}
- FFO stress 후 보유세 / FFO: {_fmt_ratio_pct(stress_row.get('FFO 대비', pd.NA))}
- Peer 요약: {peer_summary.get('summary_text', 'Peer Snapshot 기준 주요 지표 비교 필요')}

## 3. 주요 Tax 이슈
{_lines_from_issue_matrix(issue_matrix)}

## 4. 요청자료
{_lines_from_request_list(request_list)}

## 5. 실무적 시사점
- 보유세 부담은 FFO, 배당가능재원, 예산 편성 검토와 함께 확인해야 합니다.
- 자산별 공시가격, 장부가액, 실제 고지세액의 대사가 완료되기 전에는 수치 결론보다 요청자료 우선순위와 검토 방향을 중심으로 사용합니다.
- 검증 상태: {validation.get('validation_status', '검토 필요')} / 결측: {missing_text}
- 검증 메모: {warning_text}

## 6. 제한 및 유의사항
- 본 메모는 신고 목적의 확정 세액 산출, 법률의견, 세무신고서, 투자 추천을 제공하지 않습니다.
- 최종 판단에는 원자료 확인, 회사 확인, 세무 전문가 검토가 필요합니다.
- {source_limit}{estimate_limitation}
"""
