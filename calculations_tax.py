from datetime import datetime

import pandas as pd

from formatting import _is_na, _safe_float


def build_proxy_official_price_history(asset_risk: pd.DataFrame, years_back: int = 5, latest_year: int | None = None, annual_land_growth_pct: float = 3.0, official_to_appraisal_ratio_pct: float = 55.0, building_standard_ratio_pct: float = 20.0) -> pd.DataFrame:
    """공시가격 API/CSV가 없을 때 사용하는 추정치(proxy)입니다.

    실무 사용 전에는 공식 API 또는 업로드 자료로 대체해야 합니다.
    """
    latest_year = latest_year or datetime.today().year
    start_year = latest_year - years_back + 1
    rows = []
    for _, row in asset_risk.iterrows():
        land_area = _safe_float(row.get("land_area_sqm"))
        appraised = _safe_float(row.get("appraised_value_mn_krw_20251231"))
        if pd.isna(land_area) or not land_area or pd.isna(appraised):
            continue
        latest_land_standard_mn = appraised * official_to_appraisal_ratio_pct / 100
        latest_land_price_per_sqm = latest_land_standard_mn * 1_000_000 / land_area
        latest_building_standard_mn = appraised * building_standard_ratio_pct / 100
        for y in range(start_year, latest_year + 1):
            periods_back = latest_year - y
            price = latest_land_price_per_sqm / ((1 + annual_land_growth_pct / 100) ** periods_back)
            building_value = latest_building_standard_mn / ((1 + max(annual_land_growth_pct * 0.5, 0) / 100) ** periods_back)
            rows.append({
                "asset_name": row.get("asset_name"),
                "year": y,
                "official_land_price_per_sqm_krw": price,
                "building_standard_value_mn_krw": building_value,
                "official_price_source": "proxy_from_appraisal_replace_with_REB_or_official_price_API",
            })
    return pd.DataFrame(rows)


def separate_aggregate_land_property_tax_mn(tax_base_mn):
    """별도합산 토지분 재산세 본세. 입력/출력 단위: 백만원."""
    if _is_na(tax_base_mn):
        return pd.NA
    x = float(tax_base_mn)
    if x <= 200:
        return x * 0.002
    if x <= 1000:
        return 0.4 + (x - 200) * 0.003
    return 2.8 + (x - 1000) * 0.004


def build_holding_tax_estimator(asset_risk: pd.DataFrame, official_price_history: pd.DataFrame, land_fmv_ratio_pct: float = 70.0, building_fmv_ratio_pct: float = 70.0, building_tax_rate_pct: float = 0.25, include_urban_area_tax: bool = True, include_local_education_tax: bool = True, apply_tax_burden_cap: bool = False, tax_burden_cap_pct: float = 150.0) -> pd.DataFrame:
    """Build 5-year holding tax estimate from official land price / building standard value."""
    if official_price_history is None or official_price_history.empty:
        return pd.DataFrame()
    base_cols = ["asset_name", "location", "land_area_sqm", "appraised_value_mn_krw_20251231", "asset_type"]
    base = asset_risk[[c for c in base_cols if c in asset_risk.columns]].copy()
    df = official_price_history.copy()
    df = df.merge(base, on="asset_name", how="left", suffixes=("", "_asset"))
    if "land_area_sqm" not in df.columns:
        df["land_area_sqm"] = pd.NA
    df["land_area_sqm"] = pd.to_numeric(df["land_area_sqm"], errors="coerce")
    if "official_land_price_per_sqm_krw" not in df.columns:
        df["official_land_price_per_sqm_krw"] = pd.NA
    if "building_standard_value_mn_krw" not in df.columns:
        df["building_standard_value_mn_krw"] = 0.0
    df["official_land_price_per_sqm_krw"] = pd.to_numeric(df["official_land_price_per_sqm_krw"], errors="coerce")
    df["building_standard_value_mn_krw"] = pd.to_numeric(df["building_standard_value_mn_krw"], errors="coerce").fillna(0.0)
    df["토지_시가표준액_백만원"] = df["official_land_price_per_sqm_krw"] * df["land_area_sqm"] / 1_000_000
    df["건물_시가표준액_백만원"] = df["building_standard_value_mn_krw"]
    df["토지_과세표준_백만원"] = df["토지_시가표준액_백만원"] * land_fmv_ratio_pct / 100
    df["건물_과세표준_백만원"] = df["건물_시가표준액_백만원"] * building_fmv_ratio_pct / 100
    df["토지분_재산세본세_백만원"] = df["토지_과세표준_백만원"].apply(separate_aggregate_land_property_tax_mn)
    df["건물분_재산세본세_백만원"] = df["건물_과세표준_백만원"] * building_tax_rate_pct / 100
    df["재산세본세_백만원"] = df["토지분_재산세본세_백만원"].fillna(0) + df["건물분_재산세본세_백만원"].fillna(0)
    if include_urban_area_tax:
        df["도시지역분_백만원"] = (df["토지_과세표준_백만원"].fillna(0) + df["건물_과세표준_백만원"].fillna(0)) * 0.0014
    else:
        df["도시지역분_백만원"] = 0.0
    if include_local_education_tax:
        df["지방교육세_백만원"] = df["재산세본세_백만원"] * 0.20
    else:
        df["지방교육세_백만원"] = 0.0
    df["보유세_세부담상한전_백만원"] = df["재산세본세_백만원"] + df["도시지역분_백만원"] + df["지방교육세_백만원"]
    df = df.sort_values(["asset_name", "year"])
    df["보유세_추정_백만원"] = df["보유세_세부담상한전_백만원"]
    if apply_tax_burden_cap:
        capped_values = []
        for _, g in df.groupby("asset_name", sort=False):
            prev = None
            for val in g["보유세_세부담상한전_백만원"].tolist():
                if prev is None or pd.isna(prev) or pd.isna(val):
                    capped = val
                else:
                    capped = min(val, prev * tax_burden_cap_pct / 100)
                capped_values.append(capped)
                prev = capped
        df["보유세_추정_백만원"] = capped_values
    df["공시지가_전년대비_%"] = df.groupby("asset_name")["official_land_price_per_sqm_krw"].pct_change() * 100
    df["보유세_전년대비_%"] = df.groupby("asset_name")["보유세_추정_백만원"].pct_change() * 100
    first_tax = df.groupby("asset_name")["보유세_추정_백만원"].transform("first")
    df["보유세_5년누적증가_%"] = (df["보유세_추정_백만원"] / first_tax - 1) * 100
    return df


def summarize_holding_tax_history(tax_history: pd.DataFrame) -> pd.DataFrame:
    if tax_history is None or tax_history.empty:
        return pd.DataFrame()
    first_year = int(tax_history["year"].min())
    value_columns = [
        "보유세_추정_백만원",
        "토지_시가표준액_백만원",
        "토지_과세표준_백만원",
        "재산세본세_백만원",
        "도시지역분_백만원",
        "지방교육세_백만원",
    ]
    for column in value_columns:
        if column not in tax_history.columns:
            tax_history = tax_history.copy()
            tax_history[column] = pd.NA
    agg = tax_history.groupby("year", as_index=False)[value_columns].sum(min_count=1)
    first_tax = agg.loc[agg["year"] == first_year, "보유세_추정_백만원"].iloc[0]
    agg["누적증가율_%"] = (
        (agg["보유세_추정_백만원"] / first_tax - 1) * 100
        if pd.notna(first_tax) and first_tax != 0
        else pd.NA
    )
    agg["전년대비증가율_%"] = agg["보유세_추정_백만원"].pct_change() * 100
    return agg


def _format_metric(value, suffix: str = "", decimals: int = 1) -> str:
    if _is_na(value):
        return "확인 필요"
    return f"{float(value):,.{decimals}f}{suffix}"


def _tax_buffer_status(incremental_tax_to_ffo_pct, dividend_buffer_mn) -> str:
    if _is_na(incremental_tax_to_ffo_pct) or _is_na(dividend_buffer_mn):
        return "자료 보완"
    if incremental_tax_to_ffo_pct >= 5 or dividend_buffer_mn < 0:
        return "검토 필요"
    if incremental_tax_to_ffo_pct >= 2:
        return "모니터링"
    return "감당 가능"


def build_property_tax_cash_flow_scenarios(
    latest_kpi: pd.Series,
    annual_summary: pd.DataFrame,
    scenario: dict,
    ffo_annualization_factor: float = 4.0,
) -> pd.DataFrame:
    """Compare incremental holding-tax outflows with REITs FFO proxy and dividend buffer."""
    if annual_summary is None or annual_summary.empty:
        return pd.DataFrame()

    latest_year = int(annual_summary["year"].max())
    latest_tax = annual_summary.loc[annual_summary["year"] == latest_year, "보유세_추정_백만원"].iloc[0]
    reported_ffo = _safe_float(latest_kpi.get("ffo_mn_krw"))
    annualized_ffo = reported_ffo * ffo_annualization_factor if not _is_na(reported_ffo) else pd.NA
    stressed_ffo = _safe_float(scenario.get("stressed_ffo", pd.NA))
    annualized_stressed_ffo = stressed_ffo * ffo_annualization_factor if not _is_na(stressed_ffo) else pd.NA
    dividend = _safe_float(latest_kpi.get("common_dividend_total_mn_krw"))
    annualized_dividend = dividend * ffo_annualization_factor if not _is_na(dividend) else pd.NA

    shock_cases = [
        ("현재 추정", 0),
        ("공시가격/과표 +5%", 5),
        ("공시가격/과표 +10%", 10),
        ("공시가격/과표 +20%", 20),
        ("공시가격/과표 +30%", 30),
    ]
    rows = []
    for label, increase_pct in shock_cases:
        stressed_tax = latest_tax * (1 + increase_pct / 100)
        incremental_tax = stressed_tax - latest_tax
        incremental_tax_to_ffo = incremental_tax / annualized_ffo * 100 if annualized_ffo else pd.NA
        incremental_tax_to_stressed_ffo = incremental_tax / annualized_stressed_ffo * 100 if annualized_stressed_ffo else pd.NA
        dividend_buffer = annualized_ffo - annualized_dividend - incremental_tax if not _is_na(annualized_ffo) and not _is_na(annualized_dividend) else pd.NA
        stressed_dividend_buffer = annualized_stressed_ffo - annualized_dividend - incremental_tax if not _is_na(annualized_stressed_ffo) and not _is_na(annualized_dividend) else pd.NA
        rows.append(
            {
                "시나리오": label,
                "보유세_증가율_%": increase_pct,
                "보유세_추정_백만원": stressed_tax,
                "추가_현금유출_백만원": incremental_tax,
                "연환산_FFO_대비_추가유출_%": incremental_tax_to_ffo,
                "스트레스_FFO_대비_추가유출_%": incremental_tax_to_stressed_ffo,
                "배당후_FFO_여유_백만원": dividend_buffer,
                "스트레스_배당후_FFO_여유_백만원": stressed_dividend_buffer,
                "판단": _tax_buffer_status(incremental_tax_to_stressed_ffo, stressed_dividend_buffer),
            }
        )
    return pd.DataFrame(rows)


def build_reit_tax_workflow_checklist(
    latest_kpi: pd.Series,
    annual_summary: pd.DataFrame,
    cash_flow_scenarios: pd.DataFrame,
    price_data_status: str,
) -> pd.DataFrame:
    """REITs 세무, 보유세, Tax Technology 업무를 위한 실무형 체크리스트입니다."""
    latest_tax = pd.NA
    latest_growth = pd.NA
    if annual_summary is not None and not annual_summary.empty:
        latest_year = int(annual_summary["year"].max())
        latest_row = annual_summary[annual_summary["year"] == latest_year].iloc[0]
        latest_tax = latest_row.get("보유세_추정_백만원", pd.NA)
        latest_growth = latest_row.get("전년대비증가율_%", pd.NA)

    max_stress_outflow = pd.NA
    if cash_flow_scenarios is not None and not cash_flow_scenarios.empty:
        max_stress_outflow = cash_flow_scenarios["추가_현금유출_백만원"].max()

    rows = [
        {
            "업무영역": "세무신고·컴플라이언스",
            "자동화 툴": "리츠 세무 캘린더와 신고자료 요청목록",
            "리츠 실무 체크": "재산세 고지서, 종부세 해당 여부, 법인세 세무조정, 원천세·부가세 신고 일정과 책임자를 관리",
            "데이터 입력": "세목별 신고기한, 고지서, 납부영수증, 장부 계정, 임대매출 자료",
            "자동 산출물": "신고/납부 진행상태, 미수취 자료 목록, 세목별 증빙 패키지",
            "우선순위": "높음",
            "완료": False,
        },
        {
            "업무영역": "지방세·부동산 보유세",
            "자동화 툴": "공시가격/API·고지세액 대사 엔진",
            "리츠 실무 체크": f"자료 기준: {price_data_status}. 최신 보유세 {_format_metric(latest_tax, '백만원')}, 전년대비 {_format_metric(latest_growth, '%')}",
            "데이터 입력": "공시지가, 건축물 시가표준액, 면적, 과세구분, 세율, 감면, 세부담상한",
            "자동 산출물": "자산별 보유세 추정, 전년대비 변동, 고지세액 차이, 경정청구 후보",
            "우선순위": "높음",
            "완료": False,
        },
        {
            "업무영역": "FFO proxy·배당 현금세무 계획",
            "자동화 툴": "보유세 인상 시나리오별 FFO proxy 커버리지 분석",
            "리츠 실무 체크": f"최대 추가 현금유출 {_format_metric(max_stress_outflow, '백만원')}이 FFO proxy와 배당 후 여유를 잠식하는지 확인",
            "데이터 입력": "FFO proxy, 배당총액, 보유세 추정액, 공시가격/과표 인상률, 금리·임대료 스트레스",
            "자동 산출물": "추가 현금유출, FFO proxy 대비 부담률, 배당 후 여유, CFO/이사회 보고 문구",
            "우선순위": "높음",
            "완료": False,
        },
        {
            "업무영역": "세무 리스크 진단",
            "자동화 툴": "계정·거래유형별 세무 리스크 레지스터",
            "리츠 실무 체크": "과세구분, 감면요건, 위탁관리/자산관리 수수료, 특수관계자 거래, 수익·비용 귀속을 점검",
            "데이터 입력": "계정명세, 계약서, 특수관계자 목록, 세무조정계산서, 과거 세무조사 이력",
            "자동 산출물": "리스크 등급, 필요 검토자료, 담당자, 쟁점별 대응 메모",
            "우선순위": "중간",
            "완료": False,
        },
        {
            "업무영역": "M&A·구조화 세무",
            "자동화 툴": "부동산 취득/매각/현물출자 세무 DD 체크리스트",
            "리츠 실무 체크": "취득세, 등록면허세, 법인세, 부가세, 부동산집합투자기구/리츠 규제와 구조상 세무효율을 검토",
            "데이터 입력": "거래구조, 매매계약, 취득원가, 감면 검토자료, 자금흐름, 보유차량",
            "자동 산출물": "Tax DD(세무 실사) 이슈로그, 구조별 세부담 비교, 거래종결 전 필요조치",
            "우선순위": "중간",
            "완료": False,
        },
        {
            "업무영역": "세무조사·경정청구·불복",
            "자동화 툴": "고지세액 편차·환급기회 탐지",
            "리츠 실무 체크": "추정세액과 고지세액 차이, 과세표준 오류, 감면 누락, 세부담상한 적용 오류 가능성 검토",
            "데이터 입력": "고지서, 납부서, 과세대장, 지방세 감면 신청서, 과거 경정청구/불복 자료",
            "자동 산출물": "경정청구 후보, 예상 환급액, 쟁점별 증빙목록, 불복 타임라인",
            "우선순위": "중간",
            "완료": False,
        },
        {
            "업무영역": "Tax Technology(세무 자동화)",
            "자동화 툴": "세무 데이터 마트와 변경 추적",
            "리츠 실무 체크": "공시가격, 고지서, 장부, 계약, DART 자료를 자산 단위로 연결하고 변경이력과 승인흔적을 보관",
            "데이터 입력": "API/CSV 원천, ERP trial balance, 계약 master, 전자고지 파일, 계산 spreadsheet",
            "자동 산출물": "데이터 품질 점수, 누락 컬럼, 변경 로그, 검토자 sign-off",
            "우선순위": "높음",
            "완료": False,
        },
    ]
    return pd.DataFrame(rows)


def build_tax_risk_register(
    tax_history: pd.DataFrame,
    annual_summary: pd.DataFrame,
    cash_flow_scenarios: pd.DataFrame,
    price_data_status: str,
) -> pd.DataFrame:
    if tax_history is None or tax_history.empty:
        return pd.DataFrame()

    latest_year = int(tax_history["year"].max())
    latest_asset_tax = tax_history[tax_history["year"] == latest_year].copy()
    proxy_mode = "proxy" in price_data_status.lower()
    top_asset = latest_asset_tax.sort_values("보유세_추정_백만원", ascending=False).iloc[0]
    latest_growth = pd.NA
    if annual_summary is not None and not annual_summary.empty:
        latest_growth = annual_summary.sort_values("year").iloc[-1].get("전년대비증가율_%", pd.NA)
    stress_issue = False
    if cash_flow_scenarios is not None and not cash_flow_scenarios.empty:
        stress_issue = cash_flow_scenarios["판단"].isin(["검토 필요", "자료 보완"]).any()

    rows = [
        {
            "리스크/기회": "공시가격·기준시가 원천 신뢰도",
            "신호": "API/CSV 미연결" if proxy_mode else "API/CSV 데이터 사용",
            "영향": "추정세액과 실제 고지세액 차이",
            "권장 자동화": "공시가격 API/CSV 업로드 검증, 자산 master와 면적·주소 대사",
            "등급": "높음" if proxy_mode else "중간",
        },
        {
            "리스크/기회": "자산별 보유세 집중",
            "신호": f"{top_asset.get('asset_name')} 보유세 {_format_metric(top_asset.get('보유세_추정_백만원'), '백만원')}",
            "영향": "소수 자산의 과세표준 오류가 전체 세부담에 크게 영향",
            "권장 자동화": "상위 자산 고지서·과세대장 우선 대사",
            "등급": "높음",
        },
        {
            "리스크/기회": "보유세 급증",
            "신호": f"전년대비 {_format_metric(latest_growth, '%')}",
            "영향": "FFO proxy·배당가능재원 감소, 예산/공시 설명 필요",
            "권장 자동화": "전년대비 변동분 attribution 및 CFO 보고서 자동 생성",
            "등급": "높음" if not _is_na(latest_growth) and abs(float(latest_growth)) >= 10 else "중간",
        },
        {
            "리스크/기회": "세부담상한·감면·과세구분 오류",
            "신호": "별도합산 토지 추정치(proxy) 적용 중",
            "영향": "과다 납부 또는 경정청구 기회 발생",
            "권장 자동화": "자산별 과세대상 구분, 감면요건, 상한 적용 여부 체크박스화",
            "등급": "중간",
        },
        {
            "리스크/기회": "FFO proxy 커버리지 부족",
            "신호": "스트레스 시나리오 검토 필요" if stress_issue else "현재 시나리오 감당 가능",
            "영향": "배당정책, 투자자 커뮤니케이션, 차환계획에 영향",
            "권장 자동화": "보유세 인상률별 FFO proxy·배당 buffer 알림",
            "등급": "높음" if stress_issue else "중간",
        },
        {
            "리스크/기회": "경정청구·불복 후보",
            "신호": "고지세액 업로드 전 단계",
            "영향": "환급 또는 향후 세무조사 대응력",
            "권장 자동화": "고지세액 CSV를 추가해 추정세액 대비 차이를 계산",
            "등급": "중간",
        },
    ]
    return pd.DataFrame(rows)


def build_tax_automation_backlog() -> pd.DataFrame:
    rows = [
        ("1", "공시가격·고지서 수집", "공시가격 API, 지방세 고지서, CSV 업로드를 자산 master에 자동 매칭", "수작업 수집 시간 감소, 오류 조기 발견"),
        ("2", "세무 캘린더", "재산세, 종부세, 법인세, VAT, 원천세 신고·납부 마감과 담당자 관리", "누락 방지와 업무 현황 가시화"),
        ("3", "FFO proxy 보유세 Stress", "보유세·금리·임대료 시나리오가 FFO proxy와 배당가능재원에 미치는 영향 산출", "CFO/이사회 보고 자동화"),
        ("4", "경정청구 탐지", "고지세액과 자체 산출세액 차이를 자산·세목별로 분해", "환급기회 및 불복 쟁점 발굴"),
        ("5", "Tax DD(세무 실사) 팩", "취득/매각 자산의 취득세·부가세·법인세·지방세 체크리스트 생성", "거래 전 세무 이슈 누락 방지"),
        ("6", "세무 리스크 통제", "자료 원천, 산식 변경, 검토자 승인, 증빙 링크를 추적", "세무조사 대응과 내부통제 강화"),
    ]
    return pd.DataFrame(rows, columns=["순서", "자동화 과제", "구현 내용", "기대효과"])
