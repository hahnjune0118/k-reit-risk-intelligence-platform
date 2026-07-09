import pandas as pd

from formatting import _is_na
from red_flag_engine import risk_level_to_korean_label


RISK_ORDER = {"높음": 0, "주의": 1, "데이터 부족": 2, "정상": 3}


def _fmt_pct(value, decimals: int = 1) -> str:
    if _is_na(value):
        return "데이터 부족"
    return f"{float(value):.{decimals}f}%"


def _fmt_bn_from_mn(value, decimals: int = 1) -> str:
    if _is_na(value):
        return "데이터 부족"
    return f"{float(value) / 1000:,.{decimals}f}십억원"


def _fmt_eok_from_mn(value, decimals: int = 1) -> str:
    if _is_na(value):
        return "데이터 부족"
    return f"{float(value) / 100:,.{decimals}f}억원"


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
        rows.append(
            {
                "자산명": row.get("asset_name", ""),
                "기준연도": latest_year,
                "source_type": row.get("source_type", row.get("official_price_source", "")),
                "source_note": row.get("source_note", row.get("official_price_source", "")),
                "식별자/주소": row.get("location", ""),
                "비고": "공개자료 및 Snapshot 기반 예비 분석용 원천 표시",
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
    rows = [
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
    return pd.DataFrame(rows)


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


def build_tax_request_list(issue_matrix: pd.DataFrame) -> pd.DataFrame:
    data_basis_text = ""
    if issue_matrix is not None and not issue_matrix.empty and "데이터 기준" in issue_matrix.columns:
        data_basis_text = " / ".join(issue_matrix["데이터 기준"].dropna().astype(str).unique())
    estimated_scope = any(keyword in data_basis_text for keyword in ["Snapshot", "추정", "estimate", "peer_snapshot", "proxy"])
    defaults = [
        ("재산세 고지서", "추정 보유세와 실제 고지세액 대사", "보유세 정합성", "높음", "자산별·연도별 고지서"),
        ("토지대장", "토지면적, 지번, 소유 구조 확인", "공시가격 / 장부가액 괴리", "높음", "PNU 또는 소재지 대사"),
        ("건축물대장", "건물 시가표준액 및 용도 확인", "과세표준 산정", "높음", "건축물 용도별 세율 확인"),
        ("개별공시지가 조회자료", "공시가격 상승률 및 기준가격 확인", "공시가격 상승 민감도", "높음", "V-World 또는 공식 조회자료"),
        ("자산별 장부가액 명세", "투자부동산 장부가액과 공시가격 비교", "공시가격 / 장부가액 괴리", "높음", "자산 master와 연결"),
        ("임대수익 명세", "보유세 부담이 수익성에 미치는 영향 분석", "보유세 / 영업수익", "중간", "자산별 NOI가 있으면 우선 요청"),
        ("FFO 산정자료", "보유세 현금유출이 배당 여력에 미치는 영향 확인", "보유세 / FFO", "높음", "연환산 여부 확인"),
        ("취득 관련 계약서", "취득세·감면·과세표준 관련 검토", "취득 관련 지방세 검토", "중간", "취득 시점별 자료"),
        ("자산별 위치 및 면적 자료", "공시가격, 토지면적, 건물면적 대사", "자산별 과세자료 정합성", "높음", "소재지, 면적, 용도 포함"),
    ]
    rows = []
    high_or_warning = issue_matrix[issue_matrix["위험수준"].isin(["높음", "주의"])] if issue_matrix is not None and not issue_matrix.empty else pd.DataFrame()
    issue_text = " / ".join(high_or_warning["세무 이슈"].head(3).tolist()) if not high_or_warning.empty else "기본 보유세 검토"
    for item, purpose, related, priority, note in defaults:
        rows.append(
            {
                "요청자료": item,
                "요청 목적": purpose,
                "관련 이슈": issue_text if related in {"보유세 / FFO", "보유세 / 영업수익"} and issue_text else related,
                "우선순위": priority,
                "비고": f"{note} / 자산별 상세자료 부족 보완" if estimated_scope and priority == "높음" else note,
            }
        )
    if estimated_scope:
        rows.append(
            {
                "요청자료": "자산별 세부 보유세 산출자료",
                "요청 목적": "회사 전체 Snapshot 추정값을 자산별 실제 고지세액 및 과세표준과 대사",
                "관련 이슈": "자산별 상세자료 부족 보완",
                "우선순위": "높음",
                "비고": "회사 전체 추정값을 공식 세액처럼 사용하지 않기 위한 보완 요청",
            }
        )
    return pd.DataFrame(rows)


def build_tax_automation_summary(issue_matrix: pd.DataFrame, request_list: pd.DataFrame, reconciliation: pd.DataFrame, memo_available: bool = True) -> pd.DataFrame:
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


def build_tax_review_memo(
    company_profile: dict,
    data_basis: str,
    issue_matrix: pd.DataFrame,
    reconciliation: pd.DataFrame,
    request_list: pd.DataFrame,
    ffo_stress: pd.DataFrame,
    peer_summary: dict | None = None,
) -> str:
    company_name = company_profile.get("company_name", "선택 리츠")
    stock_code = company_profile.get("stock_code", "")
    peer_summary = peer_summary or {}
    high_or_warning = issue_matrix[issue_matrix["위험수준"].isin(["높음", "주의"])] if issue_matrix is not None and not issue_matrix.empty else pd.DataFrame()
    recon_latest = reconciliation.iloc[0] if reconciliation is not None and not reconciliation.empty else pd.Series(dtype="object")
    stress_row = ffo_stress.iloc[1] if ffo_stress is not None and len(ffo_stress) > 1 else pd.Series(dtype="object")

    issue_lines = "\n".join(
        f"- {row['세무 이슈']}: {row['위험수준']} - {row['발생 근거']}"
        for _, row in high_or_warning.head(6).iterrows()
    ) or "- 현재 자동 식별된 높음/주의 항목은 제한적입니다. 원자료 대사 후 판단이 필요합니다."
    request_lines = "\n".join(f"- {row['요청자료']}: {row['요청 목적']}" for _, row in request_list.head(8).iterrows())
    estimated_scope = any(keyword in str(data_basis) for keyword in ["Snapshot", "추정", "estimate", "peer_snapshot", "proxy"])
    limitation_note = (
        "현재 선택 회사의 자산별 상세 공시가격 데이터가 제한되어 회사 전체 Snapshot 기반 추정값을 사용했습니다. "
        "본 메모는 신고 목적의 세액 산출이나 법률의견이 아니라 공개자료 및 Snapshot 기반의 예비 검토 초안입니다."
        if estimated_scope
        else "본 메모는 신고 목적의 세액 산출이나 법률의견이 아니라 공개자료 기반의 예비 검토 초안입니다."
    )

    return f"""# Tax Review Memo 초안

## 1. 검토 대상
- 회사명: {company_name}
- 종목코드: {stock_code}
- 데이터 기준: {data_basis}
- 분석 범위: 보유세 부담, 공시가격 변동, FFO 현금유출, Peer Benchmark 기반 Tax Red Flag

## 2. 주요 검토 결과
- 보유세 / FFO: {_fmt_pct(recon_latest.get('보유세 / FFO', pd.NA) * 100 if pd.notna(recon_latest.get('보유세 / FFO', pd.NA)) else pd.NA)}
- 공시가격 / 장부가액: {_fmt_pct(recon_latest.get('공시가격 / 장부가액', pd.NA) * 100 if pd.notna(recon_latest.get('공시가격 / 장부가액', pd.NA)) else pd.NA)}
- 추정 보유세: {_fmt_eok_from_mn(recon_latest.get('추정 보유세(억원)', pd.NA) * 100 if pd.notna(recon_latest.get('추정 보유세(억원)', pd.NA)) else pd.NA)}
- 스트레스 후 보유세 / FFO: {_fmt_pct(stress_row.get('FFO 대비', pd.NA) * 100 if pd.notna(stress_row.get('FFO 대비', pd.NA)) else pd.NA)}
- Peer 대비 위치: {peer_summary.get('summary_text', 'Peer Snapshot 기준 주요 지표 비교 필요')}

## 3. 추가 검토 필요사항
{issue_lines}

## 4. 요청자료
{request_lines}

## 5. 한계
{limitation_note} 최종 판단에는 원자료 확인과 전문가 검토가 필요합니다.
"""
