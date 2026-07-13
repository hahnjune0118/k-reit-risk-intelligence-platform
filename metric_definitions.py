from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    category: str
    display_name: str
    definition: str
    formula: str
    data_basis: str
    included: str
    excluded: str
    interpretation: str
    limitation: str


def _num(value: Any) -> Any:
    converted = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return converted if pd.notna(converted) else pd.NA


def safe_divide(numerator: Any, denominator: Any) -> Any:
    num = _num(numerator)
    den = _num(denominator)
    if pd.isna(num) or pd.isna(den) or den == 0:
        return pd.NA
    return num / den


def derive_book_nav_proxy(total_assets: Any, total_liabilities: Any, total_equity: Any = pd.NA) -> tuple[Any, str]:
    assets = _num(total_assets)
    liabilities = _num(total_liabilities)
    equity = _num(total_equity)
    if pd.notna(assets) and pd.notna(liabilities):
        return assets - liabilities, "총자산 - 총부채"
    if pd.notna(equity):
        return equity, "자본총계"
    return pd.NA, "총부채 또는 자본총계 부족"


def derive_interest_bearing_debt(
    short_term_borrowings: Any = pd.NA,
    current_portion_long_term_debt: Any = pd.NA,
    long_term_borrowings: Any = pd.NA,
    bonds: Any = pd.NA,
    lease_liabilities: Any = pd.NA,
    fallback_interest_bearing_debt: Any = pd.NA,
) -> tuple[Any, str]:
    components = [
        ("단기차입금", _num(short_term_borrowings)),
        ("유동성장기차입금", _num(current_portion_long_term_debt)),
        ("장기차입금", _num(long_term_borrowings)),
        ("사채", _num(bonds)),
        ("리스부채", _num(lease_liabilities)),
    ]
    available = [(name, value) for name, value in components if pd.notna(value)]
    if available:
        return sum(value for _name, value in available), " + ".join(name for name, _value in available)
    fallback = _num(fallback_interest_bearing_debt)
    if pd.notna(fallback):
        return fallback, "이자부 차입부채 fallback"
    return pd.NA, "이자부 차입부채 구성항목 부족"


def derive_net_debt(
    interest_bearing_debt: Any,
    cash_and_cash_equivalents: Any = pd.NA,
    short_term_financial_assets: Any = pd.NA,
) -> tuple[Any, str]:
    debt = _num(interest_bearing_debt)
    cash = _num(cash_and_cash_equivalents)
    short_assets = _num(short_term_financial_assets)
    if pd.isna(debt) or pd.isna(cash):
        return pd.NA, "이자부 차입부채 또는 현금및현금성자산 부족"
    available_financial_assets = 0 if pd.isna(short_assets) else short_assets
    return debt - cash - available_financial_assets, "이자부 차입부채 - 현금및현금성자산 - 즉시 사용 가능한 단기금융자산"


def derive_ffo_proxy(
    snapshot_ffo_proxy: Any = pd.NA,
    operating_cash_flow: Any = pd.NA,
    operating_income: Any = pd.NA,
    net_income: Any = pd.NA,
) -> tuple[Any, str]:
    for value, method in [
        (snapshot_ffo_proxy, "Snapshot ffo_proxy"),
        (operating_cash_flow, "영업활동현금흐름"),
        (operating_income, "영업이익"),
        (net_income, "당기순이익"),
    ]:
        converted = _num(value)
        if pd.notna(converted):
            return converted, method
    return pd.NA, "FFO proxy 산정 입력값 부족"


def is_quarter_point_rate(value: Any) -> bool:
    rate = _num(value)
    if pd.isna(rate):
        return False
    return abs((rate * 4) - round(rate * 4)) < 1e-9


METRIC_DEFINITIONS: tuple[MetricDefinition, ...] = (
    MetricDefinition(
        key="book_nav_proxy",
        category="자산·부채 및 NAV",
        display_name="장부기준 NAV proxy",
        definition="재무상태표 장부가액 기준의 순자산 proxy입니다.",
        formula="총자산 - 총부채. 총자산·총부채를 모두 확보하지 못하면 자본총계를 보조 입력으로 사용합니다.",
        data_basis="DART 재무제표는 연결재무제표(CFS)를 우선하고, 연결 자료가 없으면 별도재무제표(OFS)로 fallback합니다. Snapshot은 nav 컬럼이 명시된 경우에만 사용합니다.",
        included="총부채 전체: 차입금, 사채, 리스부채, 매입채무, 충당부채, 이연법인세부채, 기타부채",
        excluded="투자부동산 최신 감정가, 매각비용, 잠재 세금효과, 비공개 시가 조정",
        interpretation="장부상 자기자본 완충력을 보는 지표입니다.",
        limitation="실질 NAV 또는 시가평가 NAV가 아니며, 투자부동산의 최신 시장가치를 반영하지 않을 수 있습니다.",
    ),
    MetricDefinition(
        key="ffo_proxy",
        category="수익성과 현금흐름",
        display_name="FFO proxy",
        definition="리츠의 반복적 현금창출력을 비교하기 위한 proxy입니다.",
        formula="Snapshot은 ffo_proxy 컬럼을 사용합니다. DART 정규화 자료는 영업활동현금흐름을 우선하고, 없으면 영업이익, 그마저 없으면 당기순이익을 사용합니다.",
        data_basis="현재 공개 데이터에는 투자부동산 감가상각비, 처분손익, 일회성 비현금 조정항목이 회사별로 충분히 구조화되어 있지 않습니다.",
        included="확보 가능한 ffo_proxy, 영업활동현금흐름, 영업이익 또는 당기순이익",
        excluded="확인되지 않은 감가상각비 가산, 처분손익 제거, 운전자본 조정, 기타 비공개 조정",
        interpretation="배당 여력, 보유세 현금유출, 이자부담을 비교하는 예비 지표입니다.",
        limitation="본 지표는 리츠가 공식적으로 공시한 FFO와 동일하지 않을 수 있으며, 확보 가능한 공시 계정과 현금흐름 자료를 이용한 비교 목적의 proxy입니다.",
    ),
    MetricDefinition(
        key="gross_ltv",
        category="REITs 핵심 지표",
        display_name="Gross LTV",
        definition="총자산 대비 이자부 차입부채 부담을 나타내는 비율입니다.",
        formula="이자부 차입부채 / 총자산",
        data_basis="DART에서는 단기차입금, 유동성장기차입금, 장기차입금, 사채, 리스부채를 구성항목으로 사용합니다. Snapshot에서는 borrowings_total을 이자부 차입부채 proxy로 사용합니다.",
        included="단기차입금, 유동성장기차입금, 장기차입금, 사채, 분석정책상 포함한 리스부채",
        excluded="충당부채, 이연법인세부채, 매입채무, 미지급비용, 기타 비차입부채",
        interpretation="차입 구조와 자본 여력을 비교하는 예비 신호입니다.",
        limitation="담보가치 기준 LTV가 아니라 총자산 기준 Gross LTV입니다. 담보별 covenant LTV와 다를 수 있습니다.",
    ),
    MetricDefinition(
        key="net_debt",
        category="자산·부채 및 NAV",
        display_name="순차입금",
        definition="이자부 차입부채에서 즉시 사용 가능한 유동성만 차감한 proxy입니다.",
        formula="이자부 차입부채 - 현금및현금성자산 - 즉시 사용 가능한 단기금융자산",
        data_basis="DART 계정명 또는 Snapshot에서 가용한 경우만 산출합니다.",
        included="현금및현금성자산, 즉시 사용 가능한 단기금융자산",
        excluded="장기금융자산, 제한예금, 담보제공예금, 처분 제한 자산",
        interpretation="차입금 상환 여력을 보수적으로 보는 지표입니다.",
        limitation="단기금융자산의 사용 제한 여부가 불명확하면 자동 차감하지 않습니다.",
    ),
    MetricDefinition(
        key="cap_rate_proxy",
        category="REITs 핵심 지표",
        display_name="Cap rate proxy",
        definition="부동산 가치 대비 수익률 proxy입니다.",
        formula="공식 NOI가 있으면 연환산 NOI / 자산가치. 현재 자산 상세 sample은 표시된 Cap rate와 평가액으로 NOI proxy를 역산합니다.",
        data_basis="회사 전체 재무제표만으로 자산별 Cap rate를 임의 생성하지 않습니다.",
        included="자산별 평가액과 자산별 Cap rate가 공시 또는 Snapshot에 있는 경우",
        excluded="본사비용, 기타사업, 일회성 손익을 자동 조정한 NOI 추정",
        interpretation="Cap rate가 상승하면 같은 NOI 기준 부동산 가치가 하락합니다.",
        limitation="공식 가치평가 Cap rate가 아니며, 자산별 원천 평가보고서와 대사가 필요합니다.",
    ),
    MetricDefinition(
        key="wale",
        category="REITs 핵심 지표",
        display_name="WALE",
        definition="가중평균 잔여 임대차기간입니다.",
        formula="Σ(임차계약 가중치 × 잔여 임대기간) / Σ(임차계약 가중치)",
        data_basis="가중치는 연간 계약임대료, 임대면적, 명시된 계약가치 순으로 사용합니다.",
        included="계약별 잔여기간과 가중치가 있는 임대차 상세자료",
        excluded="회사 전체 재무제표만으로 임의 산출한 숫자",
        interpretation="짧을수록 임대차 갱신과 공실 위험 검토가 중요합니다.",
        limitation="계약별 자료가 없으면 데이터 부족 또는 공시자료 확인 필요로 표시합니다.",
    ),
    MetricDefinition(
        key="effective_borrowing_rate_proxy",
        category="REITs 핵심 지표",
        display_name="유효차입금리 proxy",
        definition="이자부 차입부채 대비 이자비용 부담을 나타내는 proxy입니다.",
        formula="평균 이자부 차입부채가 있으면 이자비용 / 평균 이자부 차입부채. 없으면 이자비용 / 기말 이자부 차입부채.",
        data_basis="현재 공개 Snapshot은 대체로 기말잔액 기준 차입비용률 proxy입니다.",
        included="이자비용, 이자부 차입부채",
        excluded="충당부채, 이연법인세부채, 일반 영업채무",
        interpretation="차환 스프레드와 금리 민감도 검토의 기준점입니다.",
        limitation="평균잔액을 확보하지 못한 경우 평균 차입금리처럼 해석하면 안 됩니다.",
    ),
    MetricDefinition(
        key="ffo_interest_coverage_proxy",
        category="REITs 핵심 지표",
        display_name="FFO 이자감당력 proxy",
        definition="FFO proxy로 이자비용을 몇 배 충당할 수 있는지 보는 지표입니다.",
        formula="FFO proxy / 이자비용",
        data_basis="현재 선택 회사 재무 Snapshot 또는 DART 정규화 자료에서 ffo_proxy와 interest_expense가 모두 있을 때만 산출합니다.",
        included="FFO proxy, 손익계산서상 이자비용",
        excluded="현금이자지급액이 별도로 확인되지 않은 경우 현금 기준 조정",
        interpretation="1.0배 미만이면 해당 기간의 proxy 현금창출력이 이자비용보다 작다는 의미입니다.",
        limitation="이자비용과 실제 현금이자지급액은 다를 수 있습니다. 이자비용이 0 또는 결측이면 데이터 부족으로 처리합니다.",
    ),
    MetricDefinition(
        key="holding_tax_to_ffo",
        category="Tax 지표",
        display_name="보유세 / FFO proxy",
        definition="추정 보유세가 FFO proxy에서 차지하는 비중입니다.",
        formula="추정 보유세 / FFO proxy",
        data_basis="Tax Snapshot, Peer Snapshot, Holding Tax Bridge 결과를 사용합니다.",
        included="추정 보유세, FFO proxy",
        excluded="확정 고지세액으로 확인되지 않은 신고 조정",
        interpretation="비율이 높을수록 보유세 현금유출이 배당가능재원과 예산에 부담을 줄 수 있습니다.",
        limitation="신고 목적의 세액 산출이 아니라 방향성과 민감도 파악을 위한 예비 분석입니다.",
    ),
    MetricDefinition(
        key="scenario_rate_shock",
        category="시나리오 지표",
        display_name="차입 스프레드·리파이낸싱 금리 충격",
        definition="기준금리 변화와 추가 신용스프레드 변화를 합산해 변동금리 및 차환 대상 차입금에 적용하는 보수적 shock입니다.",
        formula="추정 추가 이자비용 = (변동금리 차입금 + 차환 대상 이자부 차입부채) × shock(bp) / 10,000",
        data_basis="좌측 시나리오의 기준금리 변화, 신용스프레드 변화, 차환 대상 비중을 사용합니다.",
        included="이자부 차입부채 중 변동금리 또는 차환 대상 원금",
        excluded="충당부채, 이연법인세부채, 매입채무 등 비차입부채",
        interpretation="신용스프레드와 리파이낸싱 조건 악화까지 반영한 추가 이자비용 민감도입니다.",
        limitation="세부 변동금리 노출과 전가율이 없을 때는 보수적 단순화 가정입니다.",
    ),
)


def metric_definition_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "구분": item.category,
                "지표": item.display_name,
                "정의": item.definition,
                "계산식": item.formula,
                "사용 데이터": item.data_basis,
                "포함": item.included,
                "제외": item.excluded,
                "제한사항": item.limitation,
            }
            for item in METRIC_DEFINITIONS
        ]
    )


def metric_lineage_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "지표": "장부기준 NAV proxy",
                "실제 계산식": "총자산 - 총부채. 부족 시 자본총계 보조 사용",
                "우선 데이터 소스": "DART API",
                "fallback": "Snapshot nav 컬럼 또는 데이터 부족",
                "연결/별도": "연결 우선, 별도 fallback",
                "추정 여부": "Proxy",
            },
            {
                "지표": "FFO proxy",
                "실제 계산식": "Snapshot ffo_proxy 또는 DART 영업활동현금흐름 > 영업이익 > 당기순이익",
                "우선 데이터 소스": "DART API",
                "fallback": "Peer Snapshot ffo_proxy",
                "연결/별도": "연결 우선, 별도 fallback",
                "추정 여부": "Proxy",
            },
            {
                "지표": "Gross LTV",
                "실제 계산식": "이자부 차입부채 / 총자산",
                "우선 데이터 소스": "DART API",
                "fallback": "Peer Snapshot borrowings_total / total_assets",
                "연결/별도": "연결 우선, 별도 fallback",
                "추정 여부": "산출값",
            },
            {
                "지표": "FFO 이자감당력 proxy",
                "실제 계산식": "FFO proxy / 이자비용",
                "우선 데이터 소스": "DART API 또는 KPI Snapshot",
                "fallback": "데이터 부족",
                "연결/별도": "연결 우선, 별도 fallback",
                "추정 여부": "Proxy",
            },
            {
                "지표": "보유세 / FFO proxy",
                "실제 계산식": "추정 보유세 / FFO proxy",
                "우선 데이터 소스": "Tax Snapshot",
                "fallback": "Peer Snapshot estimate",
                "연결/별도": "회사 전체 Snapshot",
                "추정 여부": "예비 추정",
            },
        ]
    )
