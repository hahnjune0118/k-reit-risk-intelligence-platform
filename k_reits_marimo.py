# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo==0.24.0",
#     "openpyxl>=3.1",
#     "pandas>=2.3",
#     "plotly>=6.0",
# ]
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="full")


with app.setup:
    import ast
    import importlib
    import io
    import os
    import stat
    import sys
    import tempfile
    import urllib.request
    import zipfile
    from pathlib import Path

    import marimo as mo
    import pandas as pd
    import plotly.graph_objects as go

    _repository_markers = (
        Path("marimo_assurance.py"),
        Path("marimo_risk.py"),
        Path("marimo_ui.py"),
        Path("src/tax_v15"),
        Path("data/v15"),
    )
    _notebook_path = Path(__file__).resolve()
    _candidate_roots = []
    for _origin in (_notebook_path.parent, Path.cwd().resolve()):
        for _candidate in (_origin, *_origin.parents[:3]):
            if _candidate not in _candidate_roots:
                _candidate_roots.append(_candidate)

    def _root_is_compatible(_candidate):
        if not all(
            (_candidate / _marker).exists() for _marker in _repository_markers
        ):
            return False
        try:
            _formatting_tree = ast.parse(
                (_candidate / "formatting.py").read_text(encoding="utf-8-sig")
            )
        except (OSError, SyntaxError, UnicodeError):
            return False
        for _node in _formatting_tree.body:
            if isinstance(_node, ast.Import) and any(
                _alias.name.split(".")[0] == "streamlit" for _alias in _node.names
            ):
                return False
            if (
                isinstance(_node, ast.ImportFrom)
                and _node.module
                and _node.module.split(".")[0] == "streamlit"
            ):
                return False
        return True

    _repository_root = next(
        (
            _candidate
            for _candidate in _candidate_roots
            if _root_is_compatible(_candidate)
        ),
        None,
    )

    def _public_path(_path):
        _resolved = str(_path.resolve())
        _home = str(Path.home().resolve())
        return _resolved.replace(_home, "<home>", 1) if _resolved.startswith(_home) else _resolved

    def _runtime_label():
        if sys.platform in {"emscripten", "wasi"}:
            return "WASM"
        _location_hint = f"{_notebook_path} {Path.cwd()}".lower()
        _molab_env_present = any(
            _name.startswith(("MOLAB", "MARIMO_CLOUD"))
            for _name in os.environ
        )
        _molab_server_path = (
            _notebook_path.as_posix() == "/marimo/notebook.py"
            or Path.cwd().resolve().as_posix() == "/marimo"
        )
        return (
            "Molab Server"
            if _molab_env_present or _molab_server_path or "molab" in _location_hint
            else "Local"
        )

    def _download_molab_repository():
        _repository = "hahnjune0118/k-reit-risk-intelligence-platform"
        _refs = (
            "main",
            "aed3f0f39bb68f1bd4e0eb2ea4f38884d82931b5",
        )
        _maximum_archive_bytes = 50 * 1024 * 1024
        for _ref in _refs:
            _archive_url = f"https://codeload.github.com/{_repository}/zip/{_ref}"
            try:
                _request = urllib.request.Request(
                    _archive_url,
                    headers={"User-Agent": "k-reits-marimo-molab-bootstrap"},
                )
                with urllib.request.urlopen(_request, timeout=30) as _response:
                    _archive_bytes = _response.read(_maximum_archive_bytes + 1)
                if len(_archive_bytes) > _maximum_archive_bytes:
                    raise ValueError("repository archive exceeds size limit")

                _extract_root = Path(tempfile.mkdtemp(prefix="k-reits-molab-"))
                with zipfile.ZipFile(io.BytesIO(_archive_bytes)) as _archive:
                    for _member in _archive.infolist():
                        _mode = _member.external_attr >> 16
                        if stat.S_ISLNK(_mode):
                            raise ValueError("repository archive contains a symbolic link")
                        _destination = (_extract_root / _member.filename).resolve()
                        if (
                            _destination != _extract_root
                            and _extract_root not in _destination.parents
                        ):
                            raise ValueError("repository archive contains an unsafe path")
                    _archive.extractall(_extract_root)

                _extracted_candidates = [
                    _path for _path in _extract_root.iterdir() if _path.is_dir()
                ]
                _downloaded_root = next(
                    (
                        _candidate
                        for _candidate in _extracted_candidates
                        if _root_is_compatible(_candidate)
                    ),
                    None,
                )
                if _downloaded_root is not None:
                    return _downloaded_root
            except (OSError, ValueError, zipfile.BadZipFile):
                continue
        return None

    if _repository_root is None and _runtime_label() == "Molab Server":
        _repository_root = _download_molab_repository()

    if _repository_root is None:
        _candidate_summary = []
        for _candidate in _candidate_roots:
            _missing = [
                _marker.as_posix()
                for _marker in _repository_markers
                if not (_candidate / _marker).exists()
            ]
            _candidate_summary.append(
                f"- {_public_path(_candidate)} (누락: {', '.join(_missing)})"
            )
        raise RuntimeError(
            "K-REIT 저장소 파일을 찾지 못했습니다.\n"
            f"실행 환경: {_runtime_label()}\n"
            "저장소 root 발견 여부: 아니요\n"
            f"현재 working directory: {_public_path(Path.cwd())}\n"
            f"notebook file 위치: {_public_path(_notebook_path)}\n"
            "확인한 후보 경로와 누락 marker:\n"
            + "\n".join(_candidate_summary)
            + "\nGitHub mirror가 notebook과 같은 branch의 repository files를 제공하는지 "
            "확인해 주세요."
        )

    _repository_root_text = str(_repository_root)
    if not sys.path or sys.path[0] != _repository_root_text:
        if _repository_root_text in sys.path:
            sys.path.remove(_repository_root_text)
        sys.path.insert(0, _repository_root_text)

    try:
        _assurance_module = importlib.import_module("marimo_assurance")
        _risk_module = importlib.import_module("marimo_risk")
        _ui_module = importlib.import_module("marimo_ui")
        _reporting_module = importlib.import_module("src.tax_v15.reporting")
    except ImportError as _local_import_error:
        _missing_module = getattr(_local_import_error, "name", None) or "저장소 내부 모듈"
        raise RuntimeError(
            "K-REIT 로컬 모듈을 불러오지 못했습니다.\n"
            f"실행 환경: {_runtime_label()}\n"
            "저장소 root 발견 여부: 예\n"
            f"누락된 모듈 또는 파일: {_missing_module}\n"
            "notebook, helper, src/tax_v15, data/v15가 같은 GitHub branch에 "
            "있는지 확인해 주세요."
        ) from None

    build_view_model_from_snapshot = _assurance_module.build_view_model_from_snapshot
    load_assurance_snapshot = _assurance_module.load_assurance_snapshot
    DashboardCharts = _risk_module.DashboardCharts
    DetailCharts = _risk_module.DetailCharts
    build_risk_view = _risk_module.build_risk_view
    load_risk_snapshot = _risk_module.load_risk_snapshot
    scenario_presets = _risk_module.scenario_presets
    bullet_list = _ui_module.bullet_list
    callout = _ui_module.callout
    compact_header = _ui_module.compact_header
    dense_metric = _ui_module.dense_metric
    dense_metric_grid = _ui_module.dense_metric_grid
    format_eok = _ui_module.format_eok
    format_krw = _ui_module.format_krw
    html_table = _ui_module.html_table
    load_css = _ui_module.load_css
    mini_stat = _ui_module.mini_stat
    panel = _ui_module.panel
    reconciliation_flow = _ui_module.reconciliation_flow
    build_tax_review_memo = _reporting_module.build_tax_review_memo
    dataframe_csv_bytes = _reporting_module.dataframe_csv_bytes
    review_document_html = _reporting_module.review_document_html
    review_pack_excel_bytes = _reporting_module.review_pack_excel_bytes


@app.cell
def _():
    mo.Html(f"<style>{load_css()}</style>")


@app.cell
def _():
    risk_snapshot = load_risk_snapshot()
    assurance_snapshot = load_assurance_snapshot()
    company_options = risk_snapshot.reit_master["company_name"].astype(str).tolist()
    return assurance_snapshot, company_options, risk_snapshot


@app.cell
def _(company_options):
    get_active_tab, set_active_tab = mo.state("1. 종합 위험 및 시나리오")
    company_select = mo.ui.dropdown(options=company_options, value="SK리츠", label="분석대상 리츠", full_width=True)
    peer_group_select = mo.ui.dropdown(options=["전체 상장리츠", "동일 자산유형"], value="전체 상장리츠", label="Peer Group", full_width=True)
    preset_select = mo.ui.dropdown(options=scenario_presets(), value="기준", label="시나리오 preset", full_width=True)
    gdp_growth = mo.ui.slider(-1.0, 5.0, step=0.1, value=2.6, label="GDP 성장률(%)", show_value=True, include_input=True, debounce=True, full_width=True)
    cpi_growth = mo.ui.slider(0.0, 6.0, step=0.1, value=2.7, label="소비자물가(%)", show_value=True, include_input=True, debounce=True, full_width=True)
    policy_rate = mo.ui.slider(1.0, 6.0, step=0.25, value=2.5, label="기준금리(%)", show_value=True, include_input=True, debounce=True, full_width=True)
    credit_spread = mo.ui.slider(-50, 200, step=25, value=25, label="신용스프레드 변화(bp)", show_value=True, include_input=True, debounce=True, full_width=True)
    refinancing_share = mo.ui.slider(0, 100, step=5, value=30, label="차환 대상 비중(%)", show_value=True, include_input=True, debounce=True, full_width=True)
    cap_rate_shock = mo.ui.slider(0, 200, step=10, value=50, label="Cap rate 충격(bp)", show_value=True, include_input=True, debounce=True, full_width=True)
    materiality_pct = mo.ui.slider(5, 30, step=1, value=10, label="평가액 비중 기준(%)", show_value=True, include_input=True, debounce=True, full_width=True)
    risk_filter = mo.ui.dropdown(options=["전체", "높음", "중간", "낮음"], value="전체", label="위험등급 filter", full_width=True)
    account_filter = mo.ui.dropdown(options=["전체", "투자부동산", "차입금", "임대수익", "특수관계자"], value="전체", label="관련 계정과목 filter", full_width=True)
    issue_filter = mo.ui.dropdown(options=["P0/P1 전체", "P0", "P1"], value="P0/P1 전체", label="미해결 사항 filter", full_width=True)
    land_change_pct = mo.ui.slider(-10, 20, step=1, value=0, label="토지 개별공시지가 변동(%)", show_value=True, include_input=True, debounce=True, full_width=True)
    building_change_pct = mo.ui.slider(-10, 20, step=1, value=0, label="건축물 시가표준액 변동(%)", show_value=True, include_input=True, debounce=True, full_width=True)
    return (
        account_filter,
        building_change_pct,
        cap_rate_shock,
        company_select,
        cpi_growth,
        credit_spread,
        gdp_growth,
        get_active_tab,
        issue_filter,
        land_change_pct,
        materiality_pct,
        peer_group_select,
        policy_rate,
        preset_select,
        refinancing_share,
        risk_filter,
        set_active_tab,
    )


@app.cell
def _(
    assurance_snapshot,
    building_change_pct,
    cap_rate_shock,
    company_select,
    cpi_growth,
    credit_spread,
    gdp_growth,
    land_change_pct,
    materiality_pct,
    peer_group_select,
    policy_rate,
    preset_select,
    refinancing_share,
    risk_snapshot,
):
    risk_view = build_risk_view(
        risk_snapshot,
        company_name=company_select.value,
        peer_group=peer_group_select.value,
        preset=preset_select.value,
        inputs={
            "gdp_growth_pct": float(gdp_growth.value),
            "cpi_pct": float(cpi_growth.value),
            "policy_rate_pct": float(policy_rate.value),
            "credit_spread_change_bp": float(credit_spread.value),
            "refinancing_share_pct": float(refinancing_share.value),
            "cap_rate_shock_bp": float(cap_rate_shock.value),
        },
        materiality_pct=float(materiality_pct.value),
    )
    assurance_view = build_view_model_from_snapshot(
        assurance_snapshot,
        custom_land_change_pct=int(land_change_pct.value),
        custom_building_change_pct=int(building_change_pct.value),
    )
    return assurance_view, risk_view


@app.cell
def _(risk_view):
    rmm_options = risk_view.rmm["감사영역"].astype(str).tolist()
    rmm_select = mo.ui.dropdown(options=rmm_options, value=rmm_options[0], label="선택 RMM 상세", full_width=True)
    lower_detail_select = mo.ui.radio(options=["최근 흐름", "자산·임차인 집중도", "차입금 만기·차환"], value="최근 흐름", label="세부 분석", inline=True)
    audit_detail_select = mo.ui.radio(options=["감사계획·위험평가", "RMM·자산 우선순위", "통제·실증절차", "KAM·내부회계"], value="감사계획·위험평가", label="감사대응 상세", inline=True)
    return audit_detail_select, lower_detail_select, rmm_select


@app.cell
def _(assurance_snapshot, assurance_view, risk_view):
    sensitivity = risk_view.sensitivity
    ffo_pivot = sensitivity.pivot(index="금리충격_bp", columns="Cap_rate_충격_bp", values="FFO_변화율")
    nav_pivot = sensitivity.pivot(index="금리충격_bp", columns="Cap_rate_충격_bp", values="NAV_변화율")
    combined_text = []
    for rate in ffo_pivot.index:
        combined_text.append([
            f"FFO {ffo_pivot.loc[rate, cap]:.1f}%<br>NAV {nav_pivot.loc[rate, cap]:.1f}%" if pd.notna(nav_pivot.loc[rate, cap]) else f"FFO {ffo_pivot.loc[rate, cap]:.1f}%<br>NAV 상세자료 없음"
            for cap in ffo_pivot.columns
        ])
    risk_heatmap_figure = go.Figure(go.Heatmap(
        z=ffo_pivot.values,
        x=[f"+{value}bp" for value in ffo_pivot.columns],
        y=[f"+{value}bp" for value in ffo_pivot.index],
        text=combined_text,
        texttemplate="%{text}",
        colorscale="Blues_r",
        colorbar={"title": "FFO %", "thickness": 12},
        hovertemplate="Cap rate %{x}<br>금리 %{y}<br>%{text}<extra></extra>",
    ))
    risk_heatmap_figure.update_layout(title="금리·Cap rate 충격 × FFO/NAV 영향", height=270, margin={"l": 48, "r": 45, "t": 42, "b": 38}, font={"family": "Inter, Noto Sans KR", "color": "#172033", "size": 12}, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", xaxis_title="Cap rate 충격", yaxis_title="금리 충격")

    risk_labels = {"Income / Lease Stability Risk": "임대수익", "Refinancing / Debt Service Risk": "차환·이자", "Valuation / NAV Sensitivity Risk": "가치·NAV", "Disclosure / Data Basis Risk": "공시자료"}
    risk_composition_figure = go.Figure(go.Bar(
        x=list(risk_view.risk_scores.values()),
        y=[risk_labels.get(key, key) for key in risk_view.risk_scores],
        orientation="h",
        marker_color=["#2f7e87", "#b87808", "#426f9b", "#7b8794"],
        text=[f"{value:.1f}" for value in risk_view.risk_scores.values()],
        textposition="auto",
    ))
    risk_composition_figure.update_layout(title="위험점수 구성", height=255, margin={"l": 88, "r": 20, "t": 42, "b": 32}, xaxis={"range": [0, 100], "gridcolor": "#e3e8ed"}, font={"family": "Inter, Noto Sans KR", "color": "#172033", "size": 12}, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", showlegend=False)

    scenario_frame = assurance_view.scenario_summary.copy()
    scenario_frame["시나리오"] = scenario_frame["Scenario"].map({"Base": "기준", "Moderate": "중간", "Severe": "심각", "Custom": "사용자"})
    scenario_frame["억원"] = scenario_frame["총 보유세"].map(float) / 100_000_000
    tax_scenario_figure = go.Figure(go.Bar(x=scenario_frame["시나리오"], y=scenario_frame["억원"], marker_color=["#1f5d89", "#0e6d70", "#8b5b08", "#71818e"], text=[f"{value:.2f}" for value in scenario_frame["억원"]], textposition="outside"))
    tax_scenario_figure.update_layout(title="보유세 시나리오 비교(억원)", height=255, margin={"l": 42, "r": 16, "t": 42, "b": 32}, yaxis={"gridcolor": "#e3e8ed"}, font={"family": "Inter, Noto Sans KR", "color": "#172033", "size": 12}, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", showlegend=False)

    tax_grid_rows = []
    for land in [-10, 0, 10, 20]:
        row = []
        for building in [-10, 0, 10, 20]:
            point = build_view_model_from_snapshot(assurance_snapshot, land, building)
            custom = point.scenario_summary[point.scenario_summary["Scenario"].eq("Custom")].iloc[0]
            row.append(float(custom["총 보유세"]) / 100_000_000)
        tax_grid_rows.append(row)
    tax_heatmap_figure = go.Figure(go.Heatmap(z=tax_grid_rows, x=["-10%", "0%", "+10%", "+20%"], y=["-10%", "0%", "+10%", "+20%"], colorscale="YlOrBr", text=[[f"{value:.2f}억" for value in row] for row in tax_grid_rows], texttemplate="%{text}", colorbar={"title": "억원", "thickness": 12}))
    tax_heatmap_figure.update_layout(title="토지가액 × 건축물가액 민감도", height=255, margin={"l": 48, "r": 45, "t": 42, "b": 36}, xaxis_title="건축물가액", yaxis_title="토지가액", font={"family": "Inter, Noto Sans KR", "color": "#172033", "size": 12}, paper_bgcolor="#ffffff")
    dashboard_charts = DashboardCharts(
        risk_heatmap=risk_heatmap_figure,
        risk_composition=risk_composition_figure,
        tax_heatmap=tax_heatmap_figure,
        tax_scenario=tax_scenario_figure,
    )
    return (dashboard_charts,)


@app.cell
def _(risk_view):
    recent = risk_view.recent_financials.copy()
    historical_figure = go.Figure()
    if risk_view.detail_available and not recent.empty:
        recent = recent.sort_values("period_end")
        historical_figure.add_trace(go.Scatter(x=recent["period_end"], y=recent["total_assets_mn_krw"], name="총자산", mode="lines+markers"))
        historical_figure.add_trace(go.Scatter(x=recent["period_end"], y=recent["interest_bearing_debt_mn_krw"], name="차입금", mode="lines+markers"))
        historical_figure.add_trace(go.Scatter(x=recent["period_end"], y=recent["total_equity_mn_krw"], name="장부 NAV proxy", mode="lines+markers"))
    else:
        historical_figure.add_annotation(text="선택 리츠의 다기간 공식 Snapshot이 부족합니다.", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    historical_figure.update_layout(height=280, margin={"l": 52, "r": 20, "t": 28, "b": 40}, font={"family": "Inter, Noto Sans KR", "color": "#172033", "size": 12}, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", yaxis={"title": "백만원", "gridcolor": "#e3e8ed"}, legend={"orientation": "h", "y": 1.12})

    asset_figure = go.Figure()
    if not risk_view.asset_concentration.empty:
        top_assets = risk_view.asset_concentration.head(8)
        asset_figure.add_trace(go.Bar(x=top_assets["portfolio_value_share_pct"], y=top_assets["asset_name"], orientation="h", marker_color="#2f7e87", text=[f"{value:.1f}%" for value in top_assets["portfolio_value_share_pct"]], textposition="auto"))
    else:
        asset_figure.add_annotation(text="회사별 상세 자산 자료 미제공", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    asset_figure.update_layout(height=280, margin={"l": 125, "r": 20, "t": 28, "b": 36}, xaxis={"title": "평가액 비중(%)", "gridcolor": "#e3e8ed"}, font={"family": "Inter, Noto Sans KR", "color": "#172033", "size": 12}, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", showlegend=False)

    maturity_figure = go.Figure()
    if not risk_view.maturity_profile.empty:
        maturity_figure.add_trace(go.Bar(x=risk_view.maturity_profile["maturity_year"].astype(str), y=risk_view.maturity_profile["principal_mn_krw"], marker_color="#426f9b", text=[f"{value/1000:.0f}십억" for value in risk_view.maturity_profile["principal_mn_krw"]], textposition="outside"))
    else:
        maturity_figure.add_annotation(text="회사별 차입금 만기 스케줄 미제공", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    maturity_figure.update_layout(height=280, margin={"l": 52, "r": 20, "t": 28, "b": 40}, yaxis={"title": "백만원", "gridcolor": "#e3e8ed"}, font={"family": "Inter, Noto Sans KR", "color": "#172033", "size": 12}, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", showlegend=False)
    detail_charts = DetailCharts(
        historical=historical_figure,
        asset_concentration=asset_figure,
        maturity=maturity_figure,
    )
    return (detail_charts,)


@app.cell
def _(assurance_view):
    review_memo = build_tax_review_memo(
        assurance_view.case.reit_name,
        assurance_view.case.tax_year,
        assurance_view.case.assets,
        assurance_view.case.parcels,
        assurance_view.case.buildings,
        assurance_view.case.taxpayers,
        assurance_view.case.calculations,
        assurance_view.case.validations,
        assurance_view.request_list,
        assurance_view.scenario_summary,
        assurance_view.issue_matrix,
    )
    prefix = "395400_SK_Seorin_2026"

    def _excel_export():
        return review_pack_excel_bytes({
            "Assets": assurance_view.case.assets,
            "Parcels": assurance_view.case.parcels,
            "Buildings": assurance_view.case.buildings,
            "Taxpayers": assurance_view.case.taxpayers,
            "Calculations": assurance_view.case.calculations,
            "ScenarioSummary": assurance_view.scenario_summary,
            "ScenarioBreakdown": assurance_view.scenario_detail,
            "TaxIssueMatrix": assurance_view.issue_matrix,
            "RequestList": assurance_view.request_list,
            "Reconciliation": assurance_view.case.reconciliation,
            "Evidence": assurance_view.evidence_matrix,
        })

    calculation_download = mo.download(lambda: dataframe_csv_bytes(assurance_view.case.calculations), filename=f"{prefix}_calculation_detail.csv", mimetype="text/csv", label="계산내역 CSV")
    scenario_download = mo.download(lambda: dataframe_csv_bytes(assurance_view.scenario_summary), filename=f"{prefix}_sensitivity.csv", mimetype="text/csv", label="시나리오 CSV")
    issue_download = mo.download(lambda: dataframe_csv_bytes(assurance_view.issue_matrix), filename=f"{prefix}_tax_issue_matrix.csv", mimetype="text/csv", label="미해결 사항 CSV")
    request_download = mo.download(lambda: dataframe_csv_bytes(assurance_view.request_list), filename=f"{prefix}_request_list.csv", mimetype="text/csv", label="요청자료 CSV")
    excel_download = mo.download(_excel_export, filename=f"{prefix}_tax_review_pack.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", label="검토팩 Excel")
    memo_download = mo.download(review_memo.encode("utf-8-sig"), filename=f"{prefix}_tax_review_memo.md", mimetype="text/markdown", label="검토메모 Markdown")
    html_download = mo.download(lambda: review_document_html("SK리츠 — SK서린빌딩 보유세 모의 감사검토", review_memo), filename=f"{prefix}_assurance_review.html", mimetype="text/html", label="검토문서 HTML")
    return calculation_download, excel_download, html_download, issue_download, memo_download, request_download, scenario_download


@app.cell
def _(
    cap_rate_shock,
    company_select,
    cpi_growth,
    credit_spread,
    gdp_growth,
    dashboard_charts,
    detail_charts,
    lower_detail_select,
    peer_group_select,
    policy_rate,
    preset_select,
    refinancing_share,
    risk_snapshot,
    risk_view,
):
    scenario = risk_view.scenario
    risk_severity = "critical" if risk_view.risk_level == "High" else "warning" if risk_view.risk_level == "Medium" else "ok"
    risk_header = mo.Html(compact_header(
        title="종합 위험 및 시나리오",
        subtitle="재무·자산·차입·시장 위험을 입력과 결과의 연결 구조로 비교합니다.",
        metadata=[f"{risk_view.company_name} ({risk_view.stock_code})", risk_view.peer_group, risk_view.scenario["scenario_label"], risk_view.detail_basis],
        source_status="official_partial",
        source_detail="공시 CSV와 Peer 저장 시점 자료를 기존 Streamlit 계산 모듈로 재수행",
        retrieved_at=risk_snapshot.retrieved_at,
    ))
    controls = mo.vstack([
        mo.md("### 분석조건"), company_select, peer_group_select, preset_select, gdp_growth, cpi_growth, policy_rate, credit_spread, refinancing_share, cap_rate_shock,
        mo.Html(callout("neutral", "계산 기준", "전망 입력은 확률가중 preset에 반영됩니다. 사용자 설정은 금리·스프레드·성장률·물가를 동일 시나리오 엔진의 충격값으로 변환합니다.")),
    ], gap=0.35).style({"border": "1px solid #b8c5d1", "border-radius": "12px", "padding": "0.8rem", "background": "#ffffff", "min-width": "0", "overflow": "hidden"})

    def _mn(value):
        return "미확인" if pd.isna(value) else f"{float(value)/1000:,.1f}십억원"

    def _pct(value):
        return "미확인" if pd.isna(value) else f"{float(value):,.1f}%"

    metrics = mo.Html('<section class="dense-panel"><div class="dense-panel-title"><h2>핵심 판단</h2><span>현재 → 시나리오 후</span></div>' + dense_metric_grid([
        dense_metric("종합 위험도", f"{risk_view.total_risk:.1f} · {risk_view.risk_level}", baseline="규칙 기반 예비점수", delta=risk_view.verdict[0], severity=risk_severity),
        dense_metric("시나리오 후 FFO", _mn(scenario["stressed_ffo"]), baseline=f"현재 {_mn(scenario['base_ffo'])}", delta=_pct(scenario["ffo_decline_pct"]), severity="warning" if pd.notna(scenario["ffo_decline_pct"]) and scenario["ffo_decline_pct"] < -5 else "ok"),
        dense_metric("FFO 이자감당력", "미확인" if pd.isna(scenario["stressed_icr"]) else f"{scenario['stressed_icr']:.2f}배", baseline="현재 " + ("미확인" if pd.isna(scenario["reported_icr"]) else f"{scenario['reported_icr']:.2f}배"), delta=scenario["interest_basis"], severity="critical" if pd.notna(scenario["stressed_icr"]) and scenario["stressed_icr"] < 1.5 else "warning" if pd.notna(scenario["stressed_icr"]) and scenario["stressed_icr"] < 2 else "ok"),
        dense_metric("장부 NAV 변화", _pct(scenario["nav_change_pct"]), baseline=_mn(scenario["base_nav"]), delta=_mn(scenario["stressed_nav"]), severity="warning" if pd.notna(scenario["nav_change_pct"]) and scenario["nav_change_pct"] <= -8 else "neutral"),
        dense_metric("투자부동산 가치 기준 차입비율", _pct(scenario["stressed_ltv_proxy"]), baseline="현재 " + _pct(scenario["base_ltv_proxy"]), delta="상세 자산 기준" if risk_view.detail_available else "상세자료 미제공", severity="warning"),
        dense_metric("배당 후 여력", _mn(scenario["dividend_cushion"]), baseline="배당부담 " + _pct(scenario["stressed_payout"]), delta="FFO proxy 기준", severity="critical" if pd.notna(scenario["dividend_cushion"]) and scenario["dividend_cushion"] < 0 else "ok"),
    ]) + '</section>')
    peer_table = mo.Html('<section class="dense-panel dense-table"><div class="dense-panel-title"><h2>Peer Benchmark</h2><span>8개 상장리츠 저장 시점 자료</span></div>' + html_table(risk_view.peer_comparison, numeric_formats={"현재": "{:,.2f}", "Peer 중앙값": "{:,.2f}", "백분위": "{:,.1f}%"}, max_rows=8, caption="Peer Benchmark 비교") + '</section>')
    risk_center = mo.vstack([metrics, peer_table], gap=0.65).style({"min-width": "0", "overflow": "hidden"})
    charts = mo.vstack([
        mo.ui.plotly(dashboard_charts.risk_heatmap, config={"responsive": True, "displaylogo": False, "displayModeBar": False}),
        mo.ui.plotly(dashboard_charts.risk_composition, config={"responsive": True, "displaylogo": False, "displayModeBar": False}),
    ], gap=0.35).style({"border": "1px solid #b8c5d1", "border-radius": "12px", "padding": "0.35rem", "background": "#ffffff", "min-width": "0", "overflow": "hidden"})
    top = mo.hstack([controls, risk_center, charts], widths=[25, 38, 37], gap=0.65, align="start", wrap=True)

    if lower_detail_select.value == "최근 흐름":
        lower_body = mo.vstack([mo.Html('<div class="decision-strip">공시된 기간별 총자산·차입금·장부 NAV proxy 흐름입니다. 인과관계가 아니라 위험 신호로만 사용합니다.</div>'), mo.ui.plotly(detail_charts.historical, config={"responsive": True, "displaylogo": False, "displayModeBar": False})], gap=0.3)
    elif lower_detail_select.value == "자산·임차인 집중도":
        concentration_summary = "상세자료 미제공"
        if not risk_view.asset_concentration.empty:
            shares = risk_view.asset_concentration["portfolio_value_share_pct"]
            concentration_summary = f"최대 자산 {shares.max():.1f}% · 상위 3개 {shares.head(3).sum():.1f}% · HHI {risk_view.asset_concentration['hhi_component'].sum():.3f}"
        lower_body = mo.hstack([
            mo.vstack([mo.Html(f'<div class="decision-strip">{concentration_summary}</div>'), mo.ui.plotly(detail_charts.asset_concentration, config={"responsive": True, "displaylogo": False, "displayModeBar": False})], gap=0.3),
            mo.Html('<div class="dense-table">' + html_table(risk_view.tenant_exposure, columns=["major_tenant", "tenant_credit", "portfolio_value_share_pct"], labels={"major_tenant": "주요 임차인", "tenant_credit": "신용도", "portfolio_value_share_pct": "평가액 비중"}, numeric_formats={"portfolio_value_share_pct": "{:,.1f}%"}, max_rows=8, caption="임차인 집중도") + '</div>'),
        ], widths=[1, 1], gap=0.6, wrap=True)
    else:
        total_debt = risk_view.debt_schedule["principal_mn_krw"].sum() if not risk_view.debt_schedule.empty else pd.NA
        near = risk_view.debt_schedule.loc[risk_view.debt_schedule["days_to_maturity"].between(0, 365), "principal_mn_krw"].sum() if not risk_view.debt_schedule.empty else pd.NA
        near_pct = near / total_debt * 100 if pd.notna(total_debt) and total_debt else pd.NA
        lower_body = mo.vstack([
            mo.Html('<div class="decision-strip">' + (f"총차입금 {total_debt/1000:,.1f}십억원 · 1년 내 만기 {near_pct:.1f}% · 차환금리 충격에 따른 추가 이자비용 {scenario['incremental_interest']:,.1f}백만원" if pd.notna(total_debt) else "회사별 차입금 만기 상세자료 미제공") + '</div>'),
            mo.ui.plotly(detail_charts.maturity, config={"responsive": True, "displaylogo": False, "displayModeBar": False}),
        ], gap=0.3)
    lower = mo.vstack([lower_detail_select, lower_body], gap=0.35).style({"border": "1px solid #b8c5d1", "border-radius": "12px", "padding": "0.65rem", "background": "#ffffff"})
    risk_page = mo.vstack([risk_header, top, lower], gap=0.55)
    return (risk_page,)


@app.cell
def _(
    account_filter,
    assurance_view,
    audit_detail_select,
    building_change_pct,
    issue_filter,
    land_change_pct,
    materiality_pct,
    risk_filter,
    risk_snapshot,
    risk_view,
    rmm_select,
    dashboard_charts,
):
    audit_header = mo.Html(compact_header(
        title="감사위험 및 보유세 재계산",
        subtitle="재무위험을 관련 계정·경영진 주장·감사대응과 연결하고 보유세를 독립적으로 재수행합니다.",
        metadata=[f"{risk_view.company_name} ({risk_view.stock_code})", "모의 감사검토", f"중점 기준 {materiality_pct.value}%", f"P0 {assurance_view.kpis['p0_open']} · P1 {assurance_view.kpis['p1_open']}"],
        source_status="official_source_calculated",
        source_detail="재무 Snapshot과 data/v15 공식 입력자료·세법 규칙 기준표(Tax Rule Master) 사용",
        retrieved_at=risk_snapshot.retrieved_at,
    ))
    scope_controls = mo.vstack([
        mo.md("### 감사범위 조정"), materiality_pct, risk_filter, account_filter, issue_filter,
        mo.md("### 보유세 민감도"), land_change_pct, building_change_pct,
        mo.Html(callout("neutral", "감사기준서 근거", "중요왜곡표시위험의 평가와 대응은 계정·주장·감사증거 상태를 함께 고려하는 모의 감사계획 단계의 선별입니다.")),
    ], gap=0.35).style({"border": "1px solid #b8c5d1", "border-radius": "12px", "padding": "0.8rem", "background": "#ffffff", "min-width": "0", "overflow": "hidden"})

    filtered_rmm = risk_view.rmm.copy()
    if account_filter.value != "전체":
        filtered_rmm = filtered_rmm[filtered_rmm["관련 계정과목"].str.contains(account_filter.value, na=False)]
    rmm_table = mo.Html('<section class="dense-panel dense-table"><div class="dense-panel-title"><h2>RMM와 감사대응</h2><span>선택 시 상세절차 연동</span></div>' + html_table(filtered_rmm, columns=["감사영역", "관련 계정과목", "경영진 주장", "발생가능성", "영향", "감사증거 상태", "권장 감사절차"], max_rows=8, caption="중요왜곡표시위험과 감사대응") + '</section>')
    selected_rmm = risk_view.rmm[risk_view.rmm["감사영역"].eq(rmm_select.value)].iloc[0]
    rmm_summary = mo.Html('<div class="mini-stat-grid">' + mini_stat("주요 중요왜곡표시위험", rmm_select.value, str(selected_rmm["RMM 신호"]), "warning") + mini_stat("현재 미해결 감사증거", f"P0 {assurance_view.kpis['p0_open']} · P1 {assurance_view.kpis['p1_open']}", "고지서·과세구분·소유관계 추가 검증", "critical") + '</div>')

    if audit_detail_select.value == "감사계획·위험평가":
        audit_detail = mo.Html(panel("선택 위험의 감사계획", f'<p><strong>관련 계정:</strong> {selected_rmm["관련 계정과목"]}</p><p><strong>경영진 주장:</strong> {selected_rmm["경영진 주장"]}</p><p><strong>위험 판단:</strong> {selected_rmm["왜 중요한가"]}</p><p><strong>대응 감사절차:</strong> {selected_rmm["권장 감사절차"]}</p>'))
    elif audit_detail_select.value == "RMM·자산 우선순위":
        priority_assets = risk_view.assurance_assets
        if risk_filter.value != "전체" and not priority_assets.empty:
            priority_assets = priority_assets[priority_assets["감사 우선순위"].eq(risk_filter.value)]
        audit_detail = mo.Html('<div class="dense-table">' + html_table(priority_assets, columns=["자산", "평가액비중_%", "Cap_rate_%", "시나리오가치변화_%", "감사중점점수", "감사 우선순위", "중점검토사유"], numeric_formats={"평가액비중_%": "{:,.1f}%", "Cap_rate_%": "{:,.2f}%", "시나리오가치변화_%": "{:,.1f}%", "감사중점점수": "{:,.0f}"}, max_rows=8, caption="자산별 감사 우선순위") + '</div>')
    elif audit_detail_select.value == "통제·실증절차":
        audit_detail = mo.Html(panel("통제테스트·실증절차·요청자료", '<p><strong>IPE 검증:</strong> 입력자료 모집단 완전성, 계산식 접근권한, 검토 증적 확인</p><p><strong>외부자료 검증:</strong> 평가보고서·차입약정·등기·고지서 원문 대사</p><p><strong>통제테스트:</strong> 변경 승인, 독립 검토, 예외 후속조치 표본검사</p><p><strong>실증절차:</strong> 재계산·외부조회·후속입금·기간귀속 테스트</p><p><strong>요청자료:</strong> 외부평가 입력, 임대차계약, 차입금 master, 보유세 과세내역서</p>'))
    else:
        audit_detail = mo.Html('<div class="dense-table">' + html_table(risk_view.kam_candidates, max_rows=6, caption="KAM 후보 모의 검토") + html_table(risk_view.icfr_controls, max_rows=8, caption="내부회계관리제도 핵심통제") + '</div>')
    audit_center = mo.vstack([rmm_summary, rmm_select, rmm_table, audit_detail_select, audit_detail], gap=0.45).style({"min-width": "0", "overflow": "hidden"})

    calc = assurance_view.verified_calculations.copy()
    tax_metrics = mo.Html('<div class="mini-stat-grid">' + mini_stat("공식자료 재계산액", format_eok(assurance_view.base_total), "원 단위 " + format_krw(assurance_view.base_total, 5), "ok") + mini_stat("실제 고지세액", "미확인", "2026 고지서 미수령", "critical") + mini_stat("고지서 대사율", str(assurance_view.kpis["notice_coverage"]), "미대사", "critical") + mini_stat("미해결 사항", f"P0 {assurance_view.kpis['p0_open']} · P1 {assurance_view.kpis['p1_open']}", "추가 감사증거 필요", "warning") + '</div>')
    calc_table = mo.Html('<div class="dense-table">' + html_table(calc, columns=["tax_name", "tax_base", "tax_rate", "calculated_tax", "calculation_status"], labels={"tax_name": "세목", "tax_base": "과세표준", "tax_rate": "세율", "calculated_tax": "산출세액", "calculation_status": "근거 상태"}, numeric_formats={"tax_base": "{:,.0f}", "tax_rate": "{:,.6f}", "calculated_tax": "{:,.0f}"}, status_columns=["calculation_status"], max_rows=9, caption="세목별 계산조서") + '</div>')
    tax_column = mo.vstack([
        tax_metrics,
        mo.ui.plotly(dashboard_charts.tax_scenario, config={"responsive": True, "displaylogo": False, "displayModeBar": False}),
        mo.ui.plotly(dashboard_charts.tax_heatmap, config={"responsive": True, "displaylogo": False, "displayModeBar": False}),
        calc_table,
        mo.accordion({"산식·법적 근거·원 단위 값": mo.Html(callout("neutral", "근거 미확보 시 계산 차단(Fail-closed)", "공식 근거가 없는 값은 장부가액, Peer 비율 또는 0으로 대체하지 않습니다. 상세 산식과 조문은 세목별 검토조서와 내보내기 파일에 보존됩니다."))}),
    ], gap=0.35).style({"border": "1px solid #b8c5d1", "border-radius": "12px", "padding": "0.5rem", "background": "#ffffff", "min-width": "0", "overflow": "hidden"})
    audit_page = mo.vstack([audit_header, mo.hstack([scope_controls, audit_center, tax_column], widths=[25, 42, 33], gap=0.65, align="start", wrap=True)], gap=0.55)
    return (audit_page,)


@app.cell
def _(
    assurance_view,
    calculation_download,
    excel_download,
    html_download,
    issue_filter,
    issue_download,
    memo_download,
    request_download,
    risk_snapshot,
    scenario_download,
):
    conclusion_header = mo.Html(compact_header(
        title="감사증거·고지서 대사 및 결론",
        subtitle="원천자료, 미해결 사항, 고지서 대사와 후속조치를 검토자 판단까지 연결합니다.",
        metadata=["SK리츠 (395400)", "SK서린빌딩", "2026 과세연도", "모의 감사검토 · 미대사"],
        source_status="official_source_calculated",
        source_detail="GitHub 검증 저장 시점 자료(data/v15/) · 공식 입력자료와 세법 규칙 기준표로 독립 재수행",
        retrieved_at=risk_snapshot.retrieved_at,
    ))
    evidence_stats = mo.Html('<div class="mini-stat-grid">' + mini_stat("핵심 입력자료 근거 확보율", str(assurance_view.kpis["evidence_coverage"]), "주소·PNU·지가·건물가액·납세의무자", "ok") + mini_stat("IPE 완전성·정확성", "5/5 확인", "계산 입력과 원천자료 연결", "ok") + mini_stat("외부자료 신뢰성", "공식 원문·해시", "검증상태와 계산 사용 여부 기록", "ok") + mini_stat("고지서 확보", "미확인", "실제 고지세액·과세코드 미입수", "critical") + '</div>')
    evidence_table = mo.Html('<div class="dense-table">' + html_table(assurance_view.evidence_matrix, columns=["metric_or_fact", "value", "source_name", "verification_status", "used_in_calculation"], labels={"metric_or_fact": "지표·사실", "source_name": "원천자료", "verification_status": "검증 상태", "used_in_calculation": "계산 사용"}, status_columns=["verification_status"], max_rows=10, caption="감사증거 매트릭스") + '</div>')
    lineage_table = mo.Html('<div class="dense-table">' + html_table(assurance_view.source_lineage, max_rows=8, caption="원천자료 계보") + '</div>')
    left = mo.vstack([evidence_stats, mo.accordion({"감사증거 매트릭스(Evidence Matrix)": evidence_table, "원천자료 계보(Source Lineage)": lineage_table})], gap=0.45).style({"border": "1px solid #b8c5d1", "border-radius": "12px", "padding": "0.6rem", "background": "#ffffff", "min-width": "0", "overflow": "hidden"})

    flow = mo.Html(reconciliation_flow(format_krw(assurance_view.base_total, 5)))
    visible_issues = assurance_view.issue_matrix
    if issue_filter.value in {"P0", "P1"}:
        visible_issues = visible_issues[visible_issues["priority"].eq(issue_filter.value)]
    issue_table = mo.Html('<section class="dense-panel dense-table"><div class="dense-panel-title"><h2>P0/P1 미해결 사항</h2><span>증거·담당절차·다음 조치 연결</span></div>' + html_table(visible_issues, columns=["priority", "tax_issue", "evidence_status", "potential_tax_effect", "required_document", "responsible_reviewer", "resolution_status"], labels={"priority": "우선순위", "tax_issue": "미해결 사항", "evidence_status": "증거 상태", "potential_tax_effect": "예상 영향", "required_document": "필요 감사증거", "responsible_reviewer": "담당 절차", "resolution_status": "상태"}, status_columns=["evidence_status", "resolution_status"], max_rows=8, caption="P0 P1 미해결 사항") + '</section>')
    conclusion_center = mo.vstack([flow, mo.Html(callout("critical", "대사 결론 보류", "실제 고지서가 확보되지 않아 실제 고지세액과 차이는 계산하지 않았으며, 대사 결론도 보류했습니다.")), issue_table], gap=0.45).style({"min-width": "0", "overflow": "hidden"})

    conclusion = mo.Html('<section class="dense-panel"><h2>검토자 결론</h2><div class="mini-stat-grid">' + mini_stat("현재 판단", "추가 감사증거 필요", "독립적 재계산 완료·고지서 대사 미완료", "warning") + mini_stat("결론 승인 상태", "보류", "모의 감사검토 단계", "critical") + '</div>' + panel("판단 근거", f'<p>공식 입력자료 기반 재수행액은 <strong>{format_eok(assurance_view.base_total)}</strong>입니다. 실제 고지서·과세구분 코드·과세기준일 등기 및 신탁상태가 미확인되어 확정세액으로 결론내리지 않습니다.</p>') + panel("미해결 감사증거 공백", bullet_list(assurance_view.snapshot_payload.get("open_items", []))) + '</section>')
    request_table = mo.Html('<div class="dense-table">' + html_table(assurance_view.request_list, columns=["priority", "required_document", "request_reason", "reviewer_status"], labels={"priority": "우선순위", "required_document": "추가 요청자료", "request_reason": "후속조치", "reviewer_status": "상태"}, status_columns=["reviewer_status"], max_rows=8, caption="추가 요청자료") + '</div>')
    exports = mo.vstack([
        mo.md("### 검토조서 내려받기"),
        mo.hstack([calculation_download, scenario_download], gap=0.4, wrap=True),
        mo.hstack([issue_download, request_download], gap=0.4, wrap=True),
        mo.hstack([excel_download, memo_download, html_download], gap=0.4, wrap=True),
        mo.Html(callout("neutral", "실행환경", "로컬 Python과 Molab Python notebook에서는 파일 생성을 지원합니다. 브라우저 전용 WASM에서는 Excel 생성 라이브러리와 파일 내려받기가 제한될 수 있습니다.")),
    ], gap=0.35).style({"border": "1px solid #b8c5d1", "border-radius": "12px", "padding": "0.65rem", "background": "#ffffff"})
    right = mo.vstack([conclusion, mo.accordion({"추가 요청자료와 후속조치": request_table}), exports], gap=0.45).style({"min-width": "0", "overflow": "hidden"})
    conclusion_page = mo.vstack([conclusion_header, mo.hstack([left, conclusion_center, right], widths=[30, 40, 30], gap=0.65, align="start", wrap=True)], gap=0.55)
    return (conclusion_page,)


@app.cell
def _(audit_page, conclusion_page, get_active_tab, risk_page, set_active_tab):
    assurance_pages = mo.ui.tabs(
        {
            "1. 종합 위험 및 시나리오": risk_page,
            "2. 감사위험 및 보유세 재계산": audit_page,
            "3. 감사증거·고지서 대사 및 결론": conclusion_page,
        },
        value=get_active_tab(),
        orientation="horizontal",
        label="K-REIT 통합 위험·감사검토",
        on_change=set_active_tab,
    )
    assurance_pages  # noqa: B018 - final Marimo cell expression renders the tabs
    return (assurance_pages,)


if __name__ == "__main__":
    app.run()
