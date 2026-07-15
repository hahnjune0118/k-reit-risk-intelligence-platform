from __future__ import annotations

import pandas as pd

from data_source_policy import contains_estimate_source, dominant_source_type


REQUEST_COLUMNS = ["요청자료", "요청 목적", "관련 이슈", "우선순위", "해당 검토영역", "source trigger", "비고"]


def _issue_text(issue_matrix: pd.DataFrame | None) -> str:
    if issue_matrix is None or issue_matrix.empty:
        return ""
    cols = [col for col in ["세무 이슈", "영향받는 지표", "발생 근거", "검토 방향", "요청자료", "데이터 기준"] if col in issue_matrix.columns]
    return " / ".join(issue_matrix[cols].astype(str).stack().dropna().tolist())


def _high_or_warning_issue(issue_matrix: pd.DataFrame | None) -> str:
    if issue_matrix is None or issue_matrix.empty or "세무 이슈" not in issue_matrix.columns:
        return "기본 보유세 검토"
    if "위험수준" in issue_matrix.columns:
        filtered = issue_matrix[issue_matrix["위험수준"].isin(["높음", "주의"])]
        if not filtered.empty:
            return " / ".join(filtered["세무 이슈"].dropna().astype(str).head(3).tolist())
    return " / ".join(issue_matrix["세무 이슈"].dropna().astype(str).head(3).tolist()) or "기본 보유세 검토"


def _append(rows: list[dict], item: str, purpose: str, issue: str, priority: str, area: str, trigger: str, note: str):
    rows.append(
        {
            "요청자료": item,
            "요청 목적": purpose,
            "관련 이슈": issue,
            "우선순위": priority,
            "해당 검토영역": area,
            "source trigger": trigger,
            "비고": note,
        }
    )


def _dedupe(rows: list[dict]) -> list[dict]:
    priority_rank = {"높음": 0, "중간": 1, "낮음": 2}
    merged: dict[str, dict] = {}
    for row in rows:
        key = row["요청자료"]
        if key not in merged:
            merged[key] = row.copy()
            continue
        target = merged[key]
        for column in ["요청 목적", "관련 이슈", "해당 검토영역", "source trigger", "비고"]:
            values = [value.strip() for value in f"{target[column]} / {row[column]}".split(" / ") if value.strip()]
            target[column] = " / ".join(dict.fromkeys(values))
        if priority_rank.get(row["우선순위"], 99) < priority_rank.get(target["우선순위"], 99):
            target["우선순위"] = row["우선순위"]
    return list(merged.values())


def map_tax_issues_to_request_items(
    issue_matrix: pd.DataFrame | None,
    source_type: str | None = None,
    data_availability: dict | None = None,
) -> pd.DataFrame:
    data_availability = data_availability or {}
    text = _issue_text(issue_matrix)
    source_text = source_type or ""
    if issue_matrix is not None and not issue_matrix.empty and "데이터 기준" in issue_matrix.columns:
        source_text = source_text or " / ".join(issue_matrix["데이터 기준"].dropna().astype(str).unique())
    canonical_source = dominant_source_type(source_text)
    estimated_scope = contains_estimate_source(source_text) or canonical_source in {"peer_snapshot_estimate", "sample_estimate", "data_insufficient"}
    fallback_used = bool(data_availability.get("fallback_used") or not data_availability.get("asset_level_tax_data_exists", False))
    high_issue = _high_or_warning_issue(issue_matrix)

    rows: list[dict] = []
    base_trigger = source_text or canonical_source

    _append(
        rows,
        "재산세 고지서",
        "추정 보유세와 실제 고지세액을 자산별·연도별로 대사",
        high_issue if "보유세" in text or "FFO" in text else "보유세 정합성",
        "높음",
        "보유세 정합성",
        base_trigger,
        "고지세액, 도시지역분, 지방교육세를 분리해 확인",
    )
    _append(
        rows,
        "개별공시지가 조회자료",
        "공시가격 상승률과 기준가격의 원천을 확인",
        "공시가격 / 장부가액 괴리",
        "높음",
        "공시가격 검증",
        base_trigger,
        "공식 조회자료 또는 기준시가 산출 근거",
    )
    _append(
        rows,
        "종합부동산세 고지서 및 과세내역",
        "재산세 외 보유세 세목의 적용 여부와 회사 전체 세부담 범위를 확인",
        "보유세 세목 coverage",
        "높음",
        "공통 필수자료",
        base_trigger,
        "종합부동산세·농어촌특별세 적용 여부와 합산·배제 내역 포함",
    )
    _append(
        rows,
        "자산별 법적 소유자·납세의무자 확인자료",
        "연결실체·법적 소유자·고지서상 납세의무자·실제 현금부담자를 구분",
        "납세의무 및 세부담 귀속",
        "높음",
        "공통 필수자료",
        base_trigger,
        "등기사항증명서, 신탁계약, SPC 구조도, 고지서 명의 대사",
    )
    _append(
        rows,
        "주요 임대차계약서의 제세공과금 부담 조항",
        "임차인 전가 또는 정산 구조가 리츠의 실제 현금유출에 미치는 영향을 확인",
        "세부담 귀속 및 임차인 전가",
        "중간",
        "공통 필수자료",
        base_trigger,
        "세금·공과금 부담 주체와 관리비 정산 조항 확인",
    )

    if "FFO" in text or "현금유출" in text or "배당" in text:
        _append(
            rows,
            "FFO proxy 산정자료",
            "보유세 현금유출이 배당가능재원에 미치는 영향을 확인하고 공식 FFO와 차이를 대사",
            high_issue,
            "높음",
            "FFO proxy 스트레스",
            base_trigger,
            "연환산 여부와 조정항목을 함께 확인",
        )
        _append(
            rows,
            "배당가능이익 산정자료",
            "추가 보유세 부담이 배당 여력에 미치는 영향을 검토",
            "FFO proxy 현금유출 스트레스",
            "중간",
            "배당 여력",
            base_trigger,
            "이익준비금, 감가상각 조정, 현금 잔액과 연결",
        )

    if "장부" in text or "공시가격" in text or "과세표준" in text:
        _append(
            rows,
            "자산별 장부가액 명세",
            "투자부동산 장부금액과 공시가격·과세표준을 대사",
            "공시가격 / 장부가액 괴리",
            "높음",
            "장부가액 대사",
            base_trigger,
            "자산 master와 재무제표 금액을 연결",
        )
        _append(
            rows,
            "토지대장",
            "토지면적, 지번, 소유 구조를 확인",
            "자산별 과세자료 정합성",
            "높음",
            "공시가격 검증",
            base_trigger,
            "PNU 또는 소재지 기준으로 대사",
        )
        _append(
            rows,
            "건축물대장",
            "건축물 용도와 면적, 시가표준액 산정 근거를 확인",
            "과세표준 산정",
            "높음",
            "과세표준 검증",
            base_trigger,
            "건축물 용도별 세율과 감면 여부 확인",
        )

    if estimated_scope or fallback_used or "자산별" in text or canonical_source == "data_insufficient":
        fallback_issue = "자산별 상세자료 부족 보완"
        _append(
            rows,
            "자산별 위치 및 면적 자료",
            "회사 전체 추정값을 자산별 공시가격·과세표준 입력값으로 전환",
            fallback_issue,
            "높음",
            "자료 보완",
            canonical_source,
            "회사 전체 추정 행을 공식 세액처럼 사용하지 않기 위한 보완 요청",
        )
        _append(
            rows,
            "자산별 장부가액 명세",
            "회사 전체 장부금액을 자산별 투자부동산 장부금액으로 분해",
            fallback_issue,
            "높음",
            "자료 보완",
            canonical_source,
            "자산별 상세자료 부족 보완",
        )
        _append(
            rows,
            "자산별 세부 보유세 산출자료",
            "회사 전체 Snapshot 추정값을 실제 고지세액 및 과세표준과 대사",
            fallback_issue,
            "높음",
            "자료 보완",
            canonical_source,
            "고지서, 과세표준, 감면, 세부담상한 적용 여부 포함",
        )
        _append(
            rows,
            "임대수익 명세",
            "보유세 부담이 자산별 수익성에 미치는 영향을 분석",
            "보유세 / 영업수익",
            "중간",
            "수익성 검토",
            canonical_source,
            "자산별 NOI가 있으면 우선 요청",
        )

    if canonical_source == "data_insufficient":
        _append(
            rows,
            "원천자료 목록",
            "부족한 입력값과 담당 원천을 먼저 식별",
            "데이터 부족",
            "높음",
            "자료 수집",
            canonical_source,
            "자료 확보 후 Tax Summary와 Memo를 재생성",
        )

    return pd.DataFrame(_dedupe(rows), columns=REQUEST_COLUMNS)
