import pandas as pd


def build_assurance_asset_priority(asset_risk: pd.DataFrame, scenario: dict, materiality_pct: float = 10.0) -> pd.DataFrame:
    """Prioritize property-level audit focus areas for RMM identification."""
    df = asset_risk.copy()
    valuation_note = scenario.get(
        "valuation_scenario_note",
        f"좌측 사이드바 시나리오의 Cap rate +{scenario.get('cap_rate_shock_bp', 'N/A')}bp 가정에서 계산",
    )
    total_value = df["appraised_value_mn_krw_20251231"].sum()
    df["평가액비중_%"] = df["appraised_value_mn_krw_20251231"] / total_value * 100 if total_value else None

    sens = scenario.get("asset_sensitivity", pd.DataFrame())
    if sens is not None and not sens.empty and "asset_name" in sens.columns:
        sens_cols = ["asset_name", "value_change_pct", "value_change_mn_krw"]
        df = df.merge(sens[sens_cols], on="asset_name", how="left")
    else:
        df["value_change_pct"] = None
        df["value_change_mn_krw"] = None

    df["assurance_priority_score"] = 0.0
    df["assurance_reasons"] = ""

    def add_flag(mask, score, reason):
        df.loc[mask, "assurance_priority_score"] += score
        df.loc[mask, "assurance_reasons"] = df.loc[mask, "assurance_reasons"].apply(lambda x: (x + "; " if x else "") + reason)

    add_flag(df["평가액비중_%"].fillna(0) >= materiality_pct, 25, "평가액 비중 큼")
    add_flag(df["cap_rate_pct_20251231"].fillna(99) < 4.0, 20, "낮은 Cap rate로 가치평가 민감")
    add_flag(df["value_change_pct"].fillna(0) <= -10, 20, "Cap rate 상승 시 가치하락 큼")
    add_flag(df["wale_yrs"].fillna(99) < 3.0, 15, "남은 임대기간 짧음")
    add_flag(df["tenant_concentration_pct"].astype(str).str.contains("100|master", case=False, na=False), 15, "임차인/마스터리스 집중")
    add_flag(df["value_uplift_pct"].fillna(0) > 25, 10, "취득가 대비 평가상승 큼")
    add_flag(df["estimated_annual_rent_mn_krw"].astype(str).str.contains("derived|추정", case=False, na=False), 10, "임대수익 자료가 직접공시보다 추정에 가까움")
    df["가치변화_시나리오메모"] = valuation_note

    df["감사 우선순위"] = pd.cut(
        df["assurance_priority_score"],
        bins=[-1, 29, 59, 1000],
        labels=["낮음", "중간", "높음"],
    ).astype(str)
    out = df[[
        "asset_name", "appraised_value_mn_krw_20251231", "평가액비중_%", "cap_rate_pct_20251231",
        "wale_yrs", "major_tenant", "value_change_pct", "가치변화_시나리오메모", "assurance_priority_score", "감사 우선순위", "assurance_reasons"
    ]].sort_values("assurance_priority_score", ascending=False)
    return out.rename(columns={
        "asset_name": "자산",
        "appraised_value_mn_krw_20251231": "평가액_백만원",
        "cap_rate_pct_20251231": "Cap_rate_%",
        "wale_yrs": "남은임대기간_년",
        "major_tenant": "주요임차인",
        "value_change_pct": "시나리오가치변화_%",
        "가치변화_시나리오메모": "가치변화 산정 메모",
        "assurance_priority_score": "감사중점점수",
        "assurance_reasons": "중점검토사유",
    })


def build_rmm_mapping(latest_kpi: pd.Series, debt_schedule: pd.DataFrame, scenario: dict, assurance_assets: pd.DataFrame) -> pd.DataFrame:
    near_1y = debt_schedule[debt_schedule["days_to_maturity"].between(0, 365, inclusive="both")]["principal_mn_krw"].sum()
    total_debt = debt_schedule["principal_mn_krw"].sum()
    near_1y_pct = near_1y / total_debt * 100 if total_debt else None
    high_priority_assets = int((assurance_assets["감사 우선순위"] == "높음").sum()) if assurance_assets is not None and not assurance_assets.empty else 0
    scenario_label = scenario.get("scenario_label", "선택 시나리오")
    cap_rate_shock_bp = scenario.get("cap_rate_shock_bp", None)
    rows = [
        {
            "감사영역": "투자부동산 공정가치",
            "RMM 신호": f"{scenario_label} / Cap rate +{cap_rate_shock_bp}bp: 감사 우선순위 높은 자산 {high_priority_assets}개, NAV 변화 {scenario.get('nav_change_pct', None):.1f}%" if pd.notna(scenario.get('nav_change_pct', None)) else "Cap rate 민감도 확인 필요",
            "왜 중요한가": "리츠 재무제표에서 투자부동산 평가액은 총자산과 순자산가치에 직접 영향을 줍니다.",
            "권장 감사절차": "외부평가보고서, Cap rate, NOI, 공실률, 임대료 성장률, 민감도 공시를 집중 검토",
        },
        {
            "감사영역": "차입금·유동성·계속기업",
            "RMM 신호": f"1년 내 만기 차입금 비중 {near_1y_pct:.1f}%, 시나리오 후 이자 감당력 {scenario.get('stressed_icr', None):.2f}x" if pd.notna(near_1y_pct) and pd.notna(scenario.get('stressed_icr', None)) else "차입금 만기와 이자 감당력 확인 필요",
            "왜 중요한가": "차환 실패나 이자비용 급증은 유동성 주석, 계속기업 검토, 후속사건 검토에 영향을 줄 수 있습니다.",
            "권장 감사절차": "차입약정, 만기연장 계획, 리파이낸싱 term sheet, 현금흐름 forecast, 배당정책 변경 가능성 확인",
        },
        {
            "감사영역": "임대수익·임대채권",
            "RMM 신호": f"평균 WALE {latest_kpi.get('wale_yrs', None):.2f}년, 임대율 {latest_kpi.get('occupancy_pct', None):.1f}%" if pd.notna(latest_kpi.get('wale_yrs', None)) else "임대율·임대기간 정보 확인 필요",
            "왜 중요한가": "임차인 이탈, 렌트프리, 계약변경은 수익 지속가능성과 미수채권 회수가능성에 영향을 줄 수 있습니다.",
            "권장 감사절차": "주요 임대차계약, 임대료 변경, 렌트프리, 미수임대료 aging, 후속 임차인 변동 확인",
        },
        {
            "감사영역": "특수관계자 거래·공시",
            "RMM 신호": "스폰서·계열 임차인 또는 마스터리스 구조 존재 여부 확인",
            "왜 중요한가": "거래조건의 시장성, 공시 완전성, 이해상충이 감사위험으로 이어질 수 있습니다.",
            "권장 감사절차": "특수관계자 식별 통제, 임대차/매입/매각 조건, 수수료, 이사회 승인, 주석 공시 확인",
        },
    ]
    return pd.DataFrame(rows)


def build_kam_candidate_table(scenario: dict, assurance_assets: pd.DataFrame, debt_schedule: pd.DataFrame, latest_kpi: pd.Series) -> pd.DataFrame:
    total_debt = debt_schedule["principal_mn_krw"].sum()
    near_1y = debt_schedule[debt_schedule["days_to_maturity"].between(0, 365, inclusive="both")]["principal_mn_krw"].sum()
    near_1y_pct = near_1y / total_debt * 100 if total_debt else 0
    high_assets = int((assurance_assets["감사 우선순위"] == "높음").sum()) if assurance_assets is not None and not assurance_assets.empty else 0
    rows = []
    rows.append({
        "후보": "투자부동산 공정가치 평가",
        "선정 신호": "강함" if high_assets > 0 or (pd.notna(scenario.get("nav_change_pct")) and scenario.get("nav_change_pct") <= -8) else "보통",
        "중점 고려사항": "Cap rate, NOI, 임대료 성장률, 공실률, 외부평가기관 가정, 민감도 공시",
        "KAM/감사보고서 문구 방향": "경영진의 주요 추정과 외부평가 가정이 시장금리·거래사례와 일관적인지 설명 필요",
    })
    rows.append({
        "후보": "차입금 차환 및 유동성",
        "선정 신호": "강함" if near_1y_pct >= 25 or (pd.notna(scenario.get("stressed_icr")) and scenario.get("stressed_icr") < 2.0) else "보통",
        "중점 고려사항": "만기집중, 차환계획, 담보여력, 약정조건, 이자비용 민감도, 배당정책",
        "KAM/감사보고서 문구 방향": "계속기업 관련 중요한 불확실성을 단정하지 않고 추가 감사절차 필요 신호로 표시",
    })
    rows.append({
        "후보": "임대수익 지속가능성 및 주요 임차인 집중",
        "선정 신호": "강함" if pd.notna(latest_kpi.get("wale_yrs", None)) and latest_kpi.get("wale_yrs") < 2.0 else "보통",
        "중점 고려사항": "WALE, 계약만기, 임차인 신용, 렌트프리, 임대료 인상조항, 미수임대료",
        "KAM/감사보고서 문구 방향": "수익 지속가능성 자체보다는 투자부동산 평가가정과 미수채권 회수가능성으로 연결해 검토",
    })
    return pd.DataFrame(rows)


def build_icfr_control_points() -> pd.DataFrame:
    rows = [
        ("투자부동산 공정가치", "외부평가기관 선정, 평가가정 검토, 민감도 분석 승인", "Cap rate·NOI·공실률 가정 변경 승인 evidence 확인"),
        ("차입금·유동성", "만기·금리·covenant 모니터링 및 리파이낸싱 계획 검토", "차입금 master file, 이사회 보고, 차환계획 업데이트 통제 확인"),
        ("임대차계약", "신규/변경/해지 계약 승인 및 임대료 조건 검토", "계약서 원본, 렌트프리, 보증금, 특수조건 입력 통제 확인"),
        ("특수관계자", "계열거래 식별, 조건 검토, 공시 완전성 검토", "특수관계자 master list와 거래내역 대사"),
        ("배당가능이익", "FFO·배당가능이익 계산 및 배당 의사결정 검토", "계산 spreadsheet 접근권한, review evidence, 이사회 승인 확인"),
    ]
    return pd.DataFrame(rows, columns=["프로세스", "핵심 통제", "감사·ICFR 테스트 포인트"])


def _metric_text(value, suffix: str = "", decimals: int = 1) -> str:
    if pd.isna(value):
        return "확인 필요"
    return f"{float(value):.{decimals}f}{suffix}"


def _near_maturity_pct(debt_schedule: pd.DataFrame) -> float | None:
    total_debt = debt_schedule["principal_mn_krw"].sum()
    if not total_debt:
        return None
    near_1y = debt_schedule[debt_schedule["days_to_maturity"].between(0, 365, inclusive="both")]["principal_mn_krw"].sum()
    return near_1y / total_debt * 100


def _priority_level(condition: bool, fallback: str = "중간") -> str:
    return "높음" if condition else fallback


def build_audit_workflow_checklist(
    latest_kpi: pd.Series,
    debt_schedule: pd.DataFrame,
    scenario: dict,
    assurance_assets: pd.DataFrame,
) -> pd.DataFrame:
    """Build a practical REIT audit checklist aligned to risk assessment and response standards."""
    near_1y_pct = _near_maturity_pct(debt_schedule)
    stressed_icr = scenario.get("stressed_icr", None)
    nav_change_pct = scenario.get("nav_change_pct", None)
    wale_yrs = latest_kpi.get("wale_yrs", None)
    occupancy_pct = latest_kpi.get("occupancy_pct", None)
    high_assets = int((assurance_assets["감사 우선순위"] == "높음").sum()) if assurance_assets is not None and not assurance_assets.empty else 0

    valuation_priority = _priority_level(high_assets > 0 or (pd.notna(nav_change_pct) and nav_change_pct <= -8))
    liquidity_priority = _priority_level(
        (pd.notna(near_1y_pct) and near_1y_pct >= 25) or (pd.notna(stressed_icr) and stressed_icr < 2.0)
    )
    lease_priority = _priority_level(
        (pd.notna(wale_yrs) and wale_yrs < 3.0) or (pd.notna(occupancy_pct) and occupancy_pct < 95)
    )

    rows = [
        {
            "감사단계": "기업과 기업환경 이해",
            "기준서 근거": "감사기준서 315.19",
            "체크 항목": "사업모델·소유/지배구조·규제환경 이해",
            "리츠 감사 포인트": "위탁관리/자산관리회사, 스폰서·계열 임차인, 배당규제, 공시 요구사항을 파악",
            "수행 절차": "정관, 투자보고서, 영업보고서, 자산관리계약, 이사회 자료, 리츠 관련 공시를 열람하고 면담으로 갱신",
            "증거/문서화": "Entity understanding memo, 지배구조 및 관련 당사자 맵",
            "우선순위": "높음",
            "완료": False,
        },
        {
            "감사단계": "기업과 기업환경 이해",
            "기준서 근거": "감사기준서 315.19",
            "체크 항목": "투자부동산 포트폴리오와 임대계약 구조 이해",
            "리츠 감사 포인트": f"우선순위 높은 자산 {high_assets}개, 평균 WALE {_metric_text(wale_yrs, '년')}, 임대율 {_metric_text(occupancy_pct, '%')}",
            "수행 절차": "자산별 평가액, 소재지, 임차인, 만기, 렌트프리, 보증금, 마스터리스 여부를 감사 중점 자산 표와 대사",
            "증거/문서화": "Asset risk matrix, lease abstract, 주요 계약 요약",
            "우선순위": valuation_priority,
            "완료": False,
        },
        {
            "감사단계": "기업과 기업환경 이해",
            "기준서 근거": "감사기준서 315.19, 315.20",
            "체크 항목": "재무성과 지표와 회계정책 이해",
            "리츠 감사 포인트": "NAV, FFO, LTV, ICR, 배당가능이익 및 투자부동산 측정 정책을 연결",
            "수행 절차": "주요 KPI 산식, 경영진 보고 지표, 투자부동산 공정가치/원가 정책, 수익인식 정책을 문서화",
            "증거/문서화": "KPI bridge, accounting policy memo",
            "우선순위": "높음",
            "완료": False,
        },
        {
            "감사단계": "기업과 기업환경 이해",
            "기준서 근거": "감사기준서 315.25",
            "체크 항목": "정보시스템과 재무보고 데이터 흐름 이해",
            "리츠 감사 포인트": "임대료 청구·수납, 차입금 master, 평가보고서, 결산 조정, 공시 작성 흐름을 파악",
            "수행 절차": "임대관리 시스템, 회계시스템, spreadsheet 사용 영역, 수기 조정 및 검토권한을 walkthrough",
            "증거/문서화": "Process flow, system/source data inventory",
            "우선순위": "중간",
            "완료": False,
        },
        {
            "감사단계": "위험평가절차",
            "기준서 근거": "감사기준서 315.13-18",
            "체크 항목": "질문·분석적 절차·관찰/검사 수행",
            "리츠 감사 포인트": f"NAV 민감도 {_metric_text(nav_change_pct, '%')}, 1년 내 만기 차입금 {_metric_text(near_1y_pct, '%')}, 스트레스 ICR {_metric_text(stressed_icr, 'x', 2)}",
            "수행 절차": "경영진/감사위원회 면담, 전년 대비 KPI 분석, 금리·cap rate·임대율 변화와 재무제표 왜곡 가능성 연결",
            "증거/문서화": "Risk assessment analytics, inquiry notes",
            "우선순위": "높음",
            "완료": False,
        },
        {
            "감사단계": "위험평가절차",
            "기준서 근거": "감사기준서 315.28-31",
            "체크 항목": "계정·공시와 경영진 주장별 RMM 식별",
            "리츠 감사 포인트": "투자부동산 평가, 임대수익/채권, 차입금/계속기업, 특수관계자 공시를 주장별로 매핑",
            "수행 절차": "RMM 매핑 표와 RMM 주장별 체크리스트를 작성하고 왜곡 발생가능성과 금액 영향을 평가",
            "증거/문서화": "RMM matrix, assertion mapping",
            "우선순위": "높음",
            "완료": False,
        },
        {
            "감사단계": "위험평가절차",
            "기준서 근거": "감사기준서 315.32",
            "체크 항목": "유의적 위험 여부 결정",
            "리츠 감사 포인트": "평가가정 민감도, 차환 불확실성, 특수관계자 조건, 수기 분개가 유의적 위험인지 판단",
            "수행 절차": "고유위험 요소, 복잡성, 주관성, 변화, 불확실성, 경영진 편의 가능성을 고려해 근거를 남김",
            "증거/문서화": "Significant risk conclusion",
            "우선순위": "높음",
            "완료": False,
        },
        {
            "감사단계": "위험평가절차",
            "기준서 근거": "감사기준서 315.33, 330.8",
            "체크 항목": "실증절차만으로 충분한 감사증거 확보가 어려운 위험 판단",
            "리츠 감사 포인트": "임대료 청구·수납, 평가 입력자료, 공시 취합, 수기 spreadsheet에 대한 통제 의존 필요성 판단",
            "수행 절차": "통제 설계·구현 확인 대상과 운영효과성 테스트 대상, 순수 실증 대응 대상을 구분",
            "증거/문서화": "Controls reliance decision",
            "우선순위": "중간",
            "완료": False,
        },
        {
            "감사단계": "위험평가절차",
            "기준서 근거": "감사기준서 315.38",
            "체크 항목": "위험평가 결론과 판단근거 문서화",
            "리츠 감사 포인트": "리츠는 거래유형이 단순한 대신 평가·차환·임대계약 이해가 RMM 결론을 좌우",
            "수행 절차": "팀 토의 내용, 이해한 핵심 요소, 정보 원천, 식별 통제, RMM 결론 및 변경 사유를 정리",
            "증거/문서화": "Planning completion memo",
            "우선순위": "높음",
            "완료": False,
        },
        {
            "감사단계": "통제테스트",
            "기준서 근거": "감사기준서 315.21-22, 330.8-10",
            "체크 항목": "통제환경과 위험평가 프로세스 점검",
            "리츠 감사 포인트": "경영진이 평가·차환·임대수익 위험을 식별하고 모니터링하는지 확인",
            "수행 절차": "감사위원회 보고, 리스크 관리 회의체, 월간 KPI 보고, covenant 모니터링 자료를 walkthrough",
            "증거/문서화": "Control environment memo",
            "우선순위": "중간",
            "완료": False,
        },
        {
            "감사단계": "통제테스트",
            "기준서 근거": "감사기준서 315.26, 330.8-10",
            "체크 항목": "투자부동산 공정가치 검토 통제",
            "리츠 감사 포인트": "외부평가기관 선정, NOI·cap rate·공실률 가정 검토, 민감도 승인 통제",
            "수행 절차": "통제 설계와 구현을 확인하고, 의존 예정이면 검토 evidence와 승인 흔적을 표본 테스트",
            "증거/문서화": "ICFR 테스트 시트, 평가가정 검토 증거",
            "우선순위": valuation_priority,
            "완료": False,
        },
        {
            "감사단계": "통제테스트",
            "기준서 근거": "감사기준서 315.26, 330.8-10",
            "체크 항목": "임대료 청구·수납·채권 aging 통제",
            "리츠 감사 포인트": "계약 조건 입력, 렌트프리 반영, 미수채권 aging, 임차인 변경 승인 통제",
            "수행 절차": "계약 master 변경 승인, 청구내역 생성, 수납대사, 미수채권 검토 통제를 표본 테스트",
            "증거/문서화": "Lease control sample, billing-to-cash reconciliation",
            "우선순위": lease_priority,
            "완료": False,
        },
        {
            "감사단계": "통제테스트",
            "기준서 근거": "감사기준서 315.26, 330.8-10",
            "체크 항목": "차입금·유동성 모니터링 통제",
            "리츠 감사 포인트": "만기, 금리, covenant, 담보여력, 리파이낸싱 계획 업데이트 통제",
            "수행 절차": "차입금 master와 약정서를 대사하고 이사회/경영진 검토 및 후속 업데이트 통제를 테스트",
            "증거/문서화": "Debt control test, covenant monitoring evidence",
            "우선순위": liquidity_priority,
            "완료": False,
        },
        {
            "감사단계": "통제테스트",
            "기준서 근거": "감사기준서 315.26",
            "체크 항목": "분개·결산·공시 작성 통제",
            "리츠 감사 포인트": "평가손익, 이자비용, 배당, 특수관계자 공시, 계속기업 주석의 수기 조정 통제",
            "수행 절차": "중요 수기분개 승인, 결산 checklist, 공시 tie-out, spreadsheet 접근권한과 검토 흔적을 확인",
            "증거/문서화": "Journal entry control, disclosure checklist",
            "우선순위": "중간",
            "완료": False,
        },
        {
            "감사단계": "실증절차",
            "기준서 근거": "감사기준서 330.6-7",
            "체크 항목": "투자부동산 평가 실증절차",
            "리츠 감사 포인트": "평가액이 NAV와 총자산을 좌우하므로 가정과 원천자료의 완전성·정확성을 검증",
            "수행 절차": "외부평가보고서, NOI, cap rate, 공실률, 임대료 성장률, 비교거래, 민감도 공시를 테스트",
            "증거/문서화": "투자부동산 평가 작업문서, 독립적 기대값",
            "우선순위": valuation_priority,
            "완료": False,
        },
        {
            "감사단계": "실증절차",
            "기준서 근거": "감사기준서 330.6-7, 570",
            "체크 항목": "차입금·차환·계속기업 실증절차",
            "리츠 감사 포인트": f"1년 내 만기 {_metric_text(near_1y_pct, '%')}, 스트레스 ICR {_metric_text(stressed_icr, 'x', 2)}",
            "수행 절차": "금융기관 조회, 약정서 검사, 만기분석, covenant 재계산, 리파이낸싱 term sheet, 현금흐름 forecast와 후속사건 확인",
            "증거/문서화": "Debt confirmation, going concern assessment",
            "우선순위": liquidity_priority,
            "완료": False,
        },
        {
            "감사단계": "실증절차",
            "기준서 근거": "감사기준서 330.6-7",
            "체크 항목": "임대수익·임대채권 실증절차",
            "리츠 감사 포인트": "리츠 재무제표의 반복 거래는 단순하지만 계약 조건과 회수가능성이 핵심",
            "수행 절차": "임대차계약, 청구서, 수납증빙, cut-off, 렌트프리, 미수채권 aging과 후속수납을 표본 테스트",
            "증거/문서화": "Revenue test sheet, AR subsequent receipt test",
            "우선순위": lease_priority,
            "완료": False,
        },
        {
            "감사단계": "실증절차",
            "기준서 근거": "감사기준서 330.6-7",
            "체크 항목": "특수관계자·공시 실증절차",
            "리츠 감사 포인트": "스폰서·계열 임차인·AMC 수수료·매입/매각 조건의 완전성과 시장성 검토",
            "수행 절차": "특수관계자 list, 이사회 의사록, 계약 조건, 거래내역, 주석 공시를 대사하고 누락 여부를 탐색",
            "증거/문서화": "Related party completeness test",
            "우선순위": "중간",
            "완료": False,
        },
        {
            "감사단계": "실증절차",
            "기준서 근거": "감사기준서 330.6-7",
            "체크 항목": "배당가능이익·FFO 재계산",
            "리츠 감사 포인트": "배당 유지가능성과 투자자 커뮤니케이션에 직접 연결되는 지표",
            "수행 절차": "FFO, 이자비용, 배당가능이익, 배당성향 산식을 재계산하고 이사회 결의와 공시 금액을 대사",
            "증거/문서화": "FFO/dividend recalculation",
            "우선순위": "중간",
            "완료": False,
        },
        {
            "감사단계": "보고·KAM·커뮤니케이션",
            "기준서 근거": "감사기준서 701",
            "체크 항목": "KAM 후보 선정 및 감사 대응 요약",
            "리츠 감사 포인트": "투자부동산 평가, 차환/유동성, 주요 임차인 집중 중 감사상 가장 유의적인 사항을 선별",
            "수행 절차": "RMM, 수행절차, 발견사항, 감사위원회 커뮤니케이션을 근거로 KAM 후보와 제외 사유를 문서화",
            "증거/문서화": "KAM selection memo",
            "우선순위": "높음",
            "완료": False,
        },
        {
            "감사단계": "보고·KAM·커뮤니케이션",
            "기준서 근거": "감사기준서 570",
            "체크 항목": "계속기업 관련 공시와 보고 영향 검토",
            "리츠 감사 포인트": "차환계획, 담보여력, 배당정책, 후속사건이 중요한 불확실성 또는 강조사항으로 이어지는지 판단",
            "수행 절차": "경영진 평가기간, forecast 가정, 차환 증빙, 주석 공시 충분성, 보고서 문단 필요성을 검토",
            "증거/문서화": "Going concern conclusion",
            "우선순위": liquidity_priority,
            "완료": False,
        },
        {
            "감사단계": "보고·KAM·커뮤니케이션",
            "기준서 근거": "감사기준서 260, 265",
            "체크 항목": "감사위원회 커뮤니케이션과 내부통제 미비점 보고",
            "리츠 감사 포인트": "유의적 위험, KAM 후보, 미수정 왜곡, 내부회계 통제 미비점을 명확히 전달",
            "수행 절차": "TCWG 보고자료, 내부통제 미비점 평가, 경영진 답변, 후속조치 계획을 정리",
            "증거/문서화": "감사위원회 커뮤니케이션, 내부통제 미비점 평가",
            "우선순위": "중간",
            "완료": False,
        },
    ]
    return pd.DataFrame(rows)


def build_rmm_assertion_checklist(
    latest_kpi: pd.Series,
    debt_schedule: pd.DataFrame,
    scenario: dict,
    assurance_assets: pd.DataFrame,
) -> pd.DataFrame:
    near_1y_pct = _near_maturity_pct(debt_schedule)
    stressed_icr = scenario.get("stressed_icr", None)
    nav_change_pct = scenario.get("nav_change_pct", None)
    wale_yrs = latest_kpi.get("wale_yrs", None)
    occupancy_pct = latest_kpi.get("occupancy_pct", None)
    high_assets = int((assurance_assets["감사 우선순위"] == "높음").sum()) if assurance_assets is not None and not assurance_assets.empty else 0

    return pd.DataFrame(
        [
            {
                "계정/공시": "투자부동산 공정가치",
                "경영진 주장": "평가, 표시와 공시",
                "RMM 판단": _priority_level(high_assets > 0 or (pd.notna(nav_change_pct) and nav_change_pct <= -8)),
                "위험 신호": f"중점 자산 {high_assets}개, NAV 민감도 {_metric_text(nav_change_pct, '%')}",
                "위험평가절차": "평가방법, 외부평가기관, NOI·cap rate·공실률 가정과 시장자료를 이해",
                "통제테스트 판단": "평가가정 검토 통제에 의존하거나 공시 취합 통제 테스트 필요",
                "실증절차": "외부평가보고서 검사, 주요 가정 독립 기대치 산정, 민감도 재계산, 공시 tie-out",
                "KAM 연계": "가능성 높음",
            },
            {
                "계정/공시": "임대수익·임대채권",
                "경영진 주장": "발생, 정확성, 기간귀속, 평가",
                "RMM 판단": _priority_level(
                    (pd.notna(wale_yrs) and wale_yrs < 3.0) or (pd.notna(occupancy_pct) and occupancy_pct < 95)
                ),
                "위험 신호": f"WALE {_metric_text(wale_yrs, '년')}, 임대율 {_metric_text(occupancy_pct, '%')}",
                "위험평가절차": "주요 임차인, 계약변경, 렌트프리, 미수채권 aging과 후속수납 위험을 이해",
                "통제테스트 판단": "계약 master 변경과 청구·수납 대사 통제 테스트 여부 결정",
                "실증절차": "계약서, 청구서, 수납증빙, cut-off, 후속수납 및 대손충당금 가정 테스트",
                "KAM 연계": "투자부동산 평가가정과 연계",
            },
            {
                "계정/공시": "차입금·이자비용·계속기업",
                "경영진 주장": "완전성, 정확성, 분류, 표시와 공시",
                "RMM 판단": _priority_level(
                    (pd.notna(near_1y_pct) and near_1y_pct >= 25) or (pd.notna(stressed_icr) and stressed_icr < 2.0)
                ),
                "위험 신호": f"1년 내 만기 {_metric_text(near_1y_pct, '%')}, 스트레스 ICR {_metric_text(stressed_icr, 'x', 2)}",
                "위험평가절차": "만기구조, covenant, 담보여력, 리파이낸싱 계획, forecast 가정을 이해",
                "통제테스트 판단": "차입금 master와 covenant 모니터링 통제 테스트 여부 결정",
                "실증절차": "금융기관 조회, 약정서 검사, covenant 재계산, 후속 차환증빙, 계속기업 주석 검토",
                "KAM 연계": "상황에 따라 KAM 또는 계속기업 보고 영향",
            },
            {
                "계정/공시": "특수관계자 거래",
                "경영진 주장": "완전성, 정확성, 표시와 공시",
                "RMM 판단": "중간",
                "위험 신호": "스폰서·계열 임차인·AMC·마스터리스 구조 확인 필요",
                "위험평가절차": "관련 당사자 식별 프로세스와 이사회 승인 구조를 이해",
                "통제테스트 판단": "관련 당사자 master list와 공시 검토 통제 테스트 여부 결정",
                "실증절차": "이사회 의사록, 계약서, 거래내역, 수수료 산식, 주석 공시 완전성 테스트",
                "KAM 연계": "거래 규모와 조건에 따라 검토",
            },
            {
                "계정/공시": "배당가능이익·FFO",
                "경영진 주장": "정확성, 표시와 공시",
                "RMM 판단": "중간",
                "위험 신호": "배당정책과 FFO가 투자자 판단과 유동성 평가에 직접 연결",
                "위험평가절차": "FFO 산식, 배당가능이익 계산, 이사회 배당 의사결정 프로세스를 이해",
                "통제테스트 판단": "계산 spreadsheet 검토 통제와 접근권한 테스트 여부 결정",
                "실증절차": "FFO/배당가능이익 재계산, 이사회 결의와 공시 대사",
                "KAM 연계": "유동성 KAM의 보조 근거",
            },
            {
                "계정/공시": "수기분개·결산조정",
                "경영진 주장": "발생, 정확성, 완전성",
                "RMM 판단": "높음",
                "위험 신호": "평가손익, 이자비용, 배당, 공시 조정이 결산 말 수기로 입력될 수 있음",
                "위험평가절차": "결산 close 절차와 journal entry 생성·승인 권한을 이해",
                "통제테스트 판단": "분개 승인 통제와 spreadsheet 변경관리 통제 테스트 여부 결정",
                "실증절차": "위험기반 JE 추출, unusual/manual entries 검사, 결산조정 근거 대사",
                "KAM 연계": "부정위험 대응 절차와 연계",
            },
        ]
    )


def build_assurance_workpaper_index() -> pd.DataFrame:
    rows = [
        ("A-100", "기업과 기업환경 이해", "기업 이해 메모", "사업모델, 규제환경, 지배구조, 정보시스템", "감사기준서 315 이해사항과 정보 원천 문서화"),
        ("A-200", "위험평가절차", "위험평가 분석표", "NAV/FFO/LTV/ICR, 금리·Cap rate 시나리오", "분석적 절차와 질문 결과가 RMM 결론으로 연결"),
        ("A-210", "위험평가절차", "RMM 주장별 매핑표", "계정/공시별 주장, 유의적 위험, 통제 의존 판단", "RMM과 후속 감사절차의 연결 관계 명확화"),
        ("C-100", "통제테스트", "Process walkthrough", "임대, 차입금, 평가, 결산, 공시 프로세스", "설계·구현 확인 및 운영효과성 테스트 범위 결정"),
        ("C-200", "통제테스트", "ICFR 테스트 시트", "핵심 통제 표본, 검토 증거, 예외사항", "통제 의존 결론 또는 실증절차 확대 판단"),
        ("D-100", "실증절차", "투자부동산 공정가치 평가", "평가보고서, NOI, Cap rate, 민감도, 공시", "평가 주장에 대한 충분하고 적합한 감사증거"),
        ("D-200", "실증절차", "Debt and going concern", "조회서, 약정서, covenant, 차환증빙, forecast", "차입금·유동성·계속기업 결론 문서화"),
        ("D-300", "실증절차", "임대수익 및 임대채권", "계약서, 청구/수납, cut-off, 후속수납", "수익·채권 주장 테스트 완료"),
        ("E-100", "보고·KAM·커뮤니케이션", "KAM 및 감사위원회 보고 메모", "KAM 후보, 감사대응, 내부통제 미비점, 보고 영향", "감사위원회 커뮤니케이션과 보고서 판단 근거"),
    ]
    return pd.DataFrame(rows, columns=["WP Ref", "감사단계", "작업문서", "연계 산출물", "완료 기준"])
