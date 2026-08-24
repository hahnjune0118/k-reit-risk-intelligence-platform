# Streamlit → Marimo Assurance 앱 전환 가이드

기준일: 2026-08-24

## 1. 전환 목표와 범위

이번 전환은 기존 Streamlit 앱을 제거하거나 화면을 일대일로 복제하는 작업이 아니다. 기존 `app.py`는 다중 리츠 탐색과 기존 네 가지 모드를 위한 공개 앱으로 유지하고, `k_reits_marimo.py`는 SK리츠·SK서린빌딩 2026년 Golden Asset Case를 감사 검토 흐름으로 재구성한 별도 Assurance 앱으로 제공한다.

두 앱은 같은 `src/tax_v15` 계산 엔진과 `data/v15` Snapshot을 사용한다. 따라서 UI 프레임워크가 달라도 법정 산식, `Decimal` 정밀도, Source lineage, 검증 상태, Fail-closed 통제와 핵심 회귀 기준값은 동일해야 한다.

| 실행 경로 | 역할 | 범위 |
|---|---|---|
| `app.py` | 기존 Streamlit 공개 앱 | 일반 정보, Assurance, Tax, 방법론 및 데이터 출처 |
| `k_reits_marimo.py` | Marimo Assurance 포트폴리오 앱 | Executive Review, Evidence Testing & Reperformance, Reconciliation & Reviewer Conclusion |

## 2. 파일 구조와 책임

| 파일 또는 디렉터리 | 책임 |
|---|---|
| `k_reits_marimo.py` | Marimo 앱 진입점, reactive widget 및 세 페이지 조합 |
| `marimo_assurance.py` | Streamlit 비의존 Snapshot 로더와 Assurance view model 생성 |
| `marimo_ui.py` | 상태 badge, KPI card, 반응형 표, 대사 흐름 등 HTML 표현 helper |
| `marimo_styles.css` | Audit workpaper와 executive dashboard 사이의 반응형 스타일 |
| `src/tax_v15/` | 공통 데이터 스키마, 계산, 시나리오, 이슈, 요청자료와 export 로직 |
| `data/v15/` | 기본이자 fallback인 정규화 CSV, Golden Asset JSON Snapshot과 Source lineage |
| `tests/test_marimo_assurance.py` | Snapshot, 기준값, widget 입력 경계, API 키 비노출 회귀 테스트 |

`marimo_assurance.py`는 화면 객체를 만들지 않는 순수 Python 계층이다. 이 분리 덕분에 Marimo 셀을 실행하지 않고도 계산 결과와 상태를 `pytest`로 검증할 수 있고, 기존 Streamlit 모듈을 import하지 않아도 된다.

## 3. 상태관리 매핑

Streamlit의 전역 rerun과 `st.session_state`를 Marimo에서 모사하지 않는다. Marimo에서는 widget의 `.value`를 참조하는 셀만 reactive dependency가 되며, 해당 값이 바뀌면 영향을 받는 계산·표·차트 셀만 다시 실행된다.

| Streamlit 패턴 | Marimo 매핑 | 전환 판단 |
|---|---|---|
| `st.radio` 기반 앱 모드와 `st.tabs` | `mo.ui.tabs({...})`에 세 page view를 결합 | 네 개 Tax 탭을 감사 검토 순서의 세 페이지로 재편하고 공통 view model을 재사용 |
| `st.slider` | `mo.ui.slider.value` → `build_view_model_from_snapshot(...)` | Snapshot을 다시 읽지 않고 Custom 입력에 의존하는 view model과 하위 출력을 갱신 |
| `st.session_state`의 회사·기간·실행 ID | 사용하지 않음 | 공개 Marimo 범위는 SK리츠·SK서린빌딩·2026년으로 고정 |
| form submit 후 전체 rerun | debounce된 widget value에 대한 dependency propagation | 별도 실행 버튼과 전역 상태 없이 최신 입력과 결과를 일치시킴 |
| `st.cache_data` 또는 암묵적 rerun 캐시 | 공통 Snapshot 로드 셀과 순수 view model | 파일 입력이 바뀌지 않는 동안 같은 데이터 객체를 하위 셀이 공유 |
| `st.download_button` | `mo.download`에 기존 bytes export 또는 지연 callable 전달 | CSV, Markdown, HTML과 Excel export를 재사용 |
| `st.error`와 예외 trace | 안전한 source status 및 사용자 메시지 | 내부 경로, secret, traceback을 공개 화면에 노출하지 않음 |

페이지 이동은 계산 상태를 별도 세션에 복사하지 않는다. 모든 페이지는 같은 view model에서 파생되므로 Executive KPI, 계산조서, Scenario, Issue Matrix와 Reviewer Conclusion 사이의 수치가 서로 어긋나지 않는다.

## 4. 재사용한 계산·데이터 모듈

Marimo UI에 산식이나 기대값을 하드코딩하지 않고 다음 기존 모듈을 직접 또는 `marimo_assurance.py`를 통해 재사용한다.

- `src.tax_v15.loaders.load_v15_bundle`: `data/v15/*.csv`를 스키마에 맞춰 로드
- `src.tax_v15.case_study.select_golden_case`: Golden Asset 범위 선택
- `src.tax_v15.case_study.build_sensitivity_scenarios`: Base, Moderate, Severe, Custom 재수행
- `src.tax_v15.case_study.build_tax_issue_matrix`: P0/P1 Issue Matrix 생성
- `src.tax_v15.case_study.build_case_request_list`: 이슈와 요청자료 연결
- `src.tax_v15.case_study.build_case_kpis`: Evidence, 고지서 대사, Open Issue KPI 생성
- `src.tax_v15.calculators`: 토지·건축물·부가세목과 종합부동산세 계산
- `src.tax_v15.reporting`: 이식 가능한 CSV, Markdown, HTML, Excel export

시나리오는 토지 개별공시지가와 건축물 시가표준액만 변경한다. 세율, 공정시장가액비율, 소유지분, 필지면적, 분리과세 판단과 소방분 계산 구조는 기존 Golden Asset 엔진을 그대로 사용한다.

## 5. 분리하거나 변경한 모듈

- `ui_*.py`는 Streamlit 렌더링과 강하게 결합되어 있으므로 Marimo가 직접 import하지 않는다.
- `api_manager.py`는 `st.secrets`와 `st.session_state`에 의존하므로 Marimo Snapshot 경로에서 import하지 않는다.
- 기존 화면용 formatting 코드를 복사하기보다 `marimo_ui.py`에 프레임워크 중립 표현 helper를 분리했다.
- Streamlit의 네 모드를 그대로 재현하지 않고 감사 흐름을 기준으로 세 페이지를 구성했다.
- 기존 Streamlit 앱과 `requirements.txt`의 Streamlit 의존성은 그대로 유지한다.

## 6. Reactive 데이터 흐름

```text
data/v15 Snapshot
  -> load_assurance_snapshot()
  -> select_golden_case()
  -> build_view_model_from_snapshot(custom inputs)
       -> KPI / scope / evidence status
       -> calculation detail / formula / source lineage
       -> Base / Moderate / Severe / Custom scenario
       -> reconciliation / P0-P1 issues / request list
  -> selected Marimo page
```

Custom slider가 바뀌면 view model의 Scenario 결과와 이를 참조하는 표·차트가 갱신된다. 고정된 범위, Source lineage와 고지서 대사 상태는 widget 입력으로 덮어쓰지 않는다.

## 7. 세 페이지 정보구조

### 7.1 Executive Review

- 분석대상, Audit Question, Related Accounts, Relevant Assertions
- 주요 위험과 RMM
- 공식 입력자료 기반 독립 재수행액 약 12.51억원
- 실제 고지세액 미확인과 고지서 대사 Coverage 0%
- Evidence Coverage, P0/P1 Open Issue, 현재 결론과 미해결 증거

12.51억원은 확정세액이나 실제 고지세액이 아니라 공식 입력자료와 Tax Rule Master에 따른 법정 절사 전 재수행액으로 표시한다.

### 7.2 Evidence Testing & Reperformance

- IPE 완전성·정확성, 외부자료 신뢰성, Source lineage
- 자산–필지–납세의무자–세목 연결
- 세목별 입력값, 단위, 출처, 검증상태, 적용 산식과 계산조서
- Base, Moderate, Severe, Custom Scenario
- Formula/Methodology와 Fail-closed 상태

### 7.3 Reconciliation & Reviewer Conclusion

- 모델 재수행액 → 실제 고지세액 → 차이 및 결론의 대사 구조
- 실제 고지서 미확보 시 `Not reconciled`
- P0/P1 Issue Matrix, 요청자료, 예상 영향, 담당 절차와 다음 조치
- 확인됨, 추정됨, 미확인 상태 label
- Reviewer Conclusion, Unresolved Evidence Gap과 지원 가능한 export

## 8. Snapshot, API 키와 Fail-closed 정책

Marimo Assurance 앱의 현재 계산 경로는 저장소에 커밋된 `data/v15` Snapshot을 기본 데이터이자 fallback으로 사용한다. API 키가 없어도 세 페이지와 모든 회귀 계산이 동작하며, 브라우저에서 API 키 입력을 요구하지 않는다.

기존 Streamlit 연결에서 사용하는 서버 환경변수 이름은 다음과 같다.

- `ECOS_API_KEY`
- `DART_API_KEY`
- `KRX_API_KEY`
- `REALTY_PRICE_API_KEY`

Marimo 앱의 현재 Golden Asset 계산은 이 키로 실시간 자료를 조회하지 않는다. 향후 live refresh를 연결하더라도 키는 서버 환경변수 또는 배포 secret으로만 주입하고 화면, 로그, export에 표시하지 않아야 한다. 연결 실패 시 마지막으로 검증된 Snapshot 상태를 명시해 사용하고, 필수 공식 Tax 근거가 Snapshot에도 없으면 추정값·장부가액·Peer 비율·0으로 채우지 않고 `data_insufficient` 또는 `manual_review_required`로 종료한다.

로더는 `data/v15` 핵심 12개 CSV와 Golden Asset JSON의 줄바꿈·BOM 정규화 bundle SHA-256을 `VERIFIED_SNAPSHOT_BUNDLE_SHA256`과 대사한다. 이어 JSON과 CSV의 핵심 ID·금액·상태, 저장 계산조서와 Tax 엔진 재수행 결과의 grain·수치·산식을 대사한다. 어떤 통제라도 실패하거나 필수 세목이 blocked 상태이면 공개 오류만 반환하고 검증 상태로 승격하지 않는다. Snapshot을 적법하게 갱신한 경우 근거·회귀 테스트를 검토한 뒤 다음 명령으로 새 digest를 확인하고 상수를 함께 갱신한다.

```powershell
py -c "from marimo_assurance import _snapshot_bundle_digest; from src.tax_v15.constants import V15_DATA_DIR; print(_snapshot_bundle_digest(V15_DATA_DIR))"
```

## 9. 기준값 대사

아래 값은 `docs/v15/TAX_LOGIC.md`, Golden Asset 데이터와 기존 테스트가 정의한 회귀 기준이다. 2026-08-24에 `build_assurance_view_model()`을 Snapshot 기본값으로 직접 실행하여 raw `Decimal` 값과 상태가 일치함을 확인했다.

| 검증 항목 | 기준값 | 현재 대사 결과 |
|---|---:|---|
| Base 총 보유세 | `1,250,710,968.55472원` | PASS — 일치 |
| Moderate 총 보유세 | `1,313,250,671.982456원` | PASS — 일치 |
| Severe 총 보유세 | `1,375,790,375.410192원` | PASS — 일치 |
| Moderate 증감액 | `62,539,703.427736원` | PASS — 일치 |
| Severe 증감액 | `125,079,406.855472원` | PASS — 일치 |
| P0 Open | `3건` | PASS — 일치 |
| P1 Open | `3건` | PASS — 일치 |
| 실제 고지서 대사 | `0% / Not reconciled` | PASS — Fail-closed 유지 |

UI의 `약 12.51억원`은 Base raw 값의 표시 형식일 뿐 별도 계산값이 아니다.

## 10. 설치, 실행과 검증

Windows PowerShell 기준:

```powershell
py -m pip install -r requirements.txt
py -m marimo run k_reits_marimo.py
```

편집 UI가 필요한 개발 환경에서는 다음을 사용한다.

```powershell
py -m marimo edit k_reits_marimo.py
```

Snapshot 전용 실행에도 별도 flag나 API 키가 필요하지 않다. notebook은 저장소 marker를 사용해 root를 찾고 CSS와 데이터 loader는 module 위치 기준 절대경로를 사용하므로, 저장소 루트 또는 저장소 밖 working directory에서 notebook 절대경로로 실행할 수 있다.

```powershell
py -m compileall -q .
py -m pytest -q
py -m ruff check k_reits_marimo.py marimo_assurance.py marimo_ui.py tests/test_marimo_assurance.py tests/test_marimo_ui.py
py -m marimo check --strict k_reits_marimo.py
py -m pytest -q tests/test_marimo_assurance.py
```

수동 smoke test에서는 `py -m marimo run k_reits_marimo.py`와 `py -m streamlit run app.py`를 각각 실행하여 세 페이지 렌더링, Custom slider 반응, 표 overflow, export, secret·trace 비노출과 기존 앱 시작을 확인한다. 자동 HTTP smoke test를 구성할 때는 로컬 격리 환경에서만 다음처럼 token을 끄고 서버의 HTTP 200 응답을 확인한다.

```powershell
py -m marimo run --headless --host 127.0.0.1 --port 2718 --no-token k_reits_marimo.py
```

## 11. 알려진 한계

- 공개 Marimo 범위는 SK리츠·SK서린빌딩·2026년 Golden Asset 한 건이다.
- 공식 입력 Evidence 5/5는 실제 고지서 대사나 법적 결론의 완결성을 의미하지 않는다.
- 실제 재산세·지역자원시설세 고지서, 분리과세 코드, 등기·신탁상태가 미확인이다.
- 법정 절사, 감면, 세부담상한과 지방자치단체 조정은 반영하지 않았다.
- 실시간 API refresh는 현재 Marimo 실행 경로의 일부가 아니며 Snapshot 최신성은 저장소 갱신 시점에 좌우된다.
- Streamlit의 General, 전체 리츠 비교와 기존 Assurance 화면은 Marimo 세 페이지로 이식하지 않았다.
- 넓은 표는 모바일에서 가로 스크롤을 사용하므로 핵심 결론은 상단 카드와 상태 label을 우선 확인해야 한다.
- 브라우저 전용 WASM 배포는 로컬 모듈, 파일 기반 Snapshot과 Excel export 호환성을 별도로 검증하기 전에는 지원 대상으로 간주하지 않는다.
- Molab 세션은 최대 12시간이며 90분 동안 유휴 상태이면 종료될 수 있으므로 장기 실행 서비스나 영구 저장소로 사용하지 않는다.

## 12. Molab 배포 준비

이 앱은 단일 notebook 파일만으로 완결되지 않는다. Molab 또는 GitHub mirror에 배포할 때 다음 파일을 같은 프로젝트 구조로 제공해야 한다.

- `k_reits_marimo.py`
- `marimo_assurance.py`
- `marimo_ui.py`
- `marimo_styles.css`
- `src/__init__.py`와 `src/tax_v15/**`
- `data/v15/*.csv`
- `data/v15/golden_asset/*.json`

필요 Python 및 package 조건은 다음과 같다.

- Python `>=3.10`
- `marimo==0.24.0`
- `pandas>=2.3`
- `plotly>=6.0`
- `openpyxl>=3.1` — Excel export 사용 시

공식 Molab GitHub mirror URL은 `https://molab.marimo.io/github/hahnjune0118/k-reit-risk-intelligence-platform/blob/main/k_reits_marimo.py/server`이며 저장소 파일과 Python 파일 export를 사용하는 이 앱은 Server 모드를 권장한다. setup bootstrap은 notebook 위치와 CWD의 제한된 상위 경로에서 `marimo_assurance.py`, `marimo_risk.py`, `marimo_ui.py`, `src/tax_v15`, `data/v15` marker가 모두 있고 top-level Streamlit import가 없는 호환 root만 선택한다. 실제 Server smoke test에서는 mirror가 notebook만 `/marimo/notebook.py`로 배치했다. 이 경로에서만 공식 GitHub archive를 최대 50 MiB로 내려받아 zip-slip·symlink를 차단하고 marker와 Molab 호환성을 다시 검증한다. 병합 전에는 검증 commit fallback, 병합 후에는 `main` archive가 우선된다. `codeload.github.com` 접근이 실패하거나 호환 root가 없으면 package 설치를 유발하는 `ModuleNotFoundError` 대신 실행환경, 확인 경로와 누락 marker를 정리한 안전한 진단 오류를 낸다.

검증된 root를 `sys.path[0]`에 등록한 뒤 `importlib.import_module()`로 로컬 모듈을 불러오므로 Marimo가 이를 외부 dependency로 정적으로 추론하지 않는다. CSS와 Snapshot은 내려받은 repository root 안에서 기존 module-relative loader를 그대로 사용한다.

Portable dependency 설치를 위해 `k_reits_marimo.py`의 PEP 723 inline metadata에는 `marimo`, `pandas`, `plotly`, `openpyxl`만 기록한다. `marimo-assurance`, `marimo-risk`, `marimo-ui`, `src`는 PyPI dependency가 아니므로 추가하지 않는다. `requirements.txt`는 로컬·서버 배포에 사용하지만 Molab notebook의 유일한 의존성 계약으로 가정하지 않는다. Python 3.10 이상을 지원하고 Python 3.13에서 notebook import, Snapshot 로드와 strict check를 검증한다.

CSV, Markdown, HTML과 Excel 검토팩 export는 Server 모드에서 지원한다. 브라우저 전용 WASM은 repository module, 파일 Snapshot 및 `openpyxl` Excel export 호환성이 확인되지 않아 현재 지원하지 않는다. Molab bootstrap은 `codeload.github.com` 네트워크 접근을 필요로 한다. 공개 URL smoke test 전에는 `Molab-ready` 또는 정상 배포 완료라고 주장하지 않는다. Molab notebook은 공개될 수 있으므로 API 키나 `.streamlit/secrets.toml`은 업로드하지 않고 배포 secret 또는 환경변수만 사용한다.

정적 session preview를 별도로 제공할 때는 `marimo export session k_reits_marimo.py`가 생성하는 `__marimo__/session/*.json`을 검토한 뒤 명시적으로 포함할 수 있다. 이 경로는 secret이나 실행 출력의 우발적 커밋을 막기 위해 기본적으로 `.gitignore`에 포함되어 있으므로, 공개 범위 검토가 끝난 파일만 `git add -f`로 추가한다. 현재 앱은 로컬 파일과 Python 모듈을 사용하므로 별도 WASM 호환성 검증 전에는 저장소 전체를 제공하는 server-backed 실행을 기본으로 한다.

배포 전 체크리스트:

1. 위 파일과 `data/v15`를 notebook과 동일 branch·상대경로로 커밋한다.
2. PEP 723 metadata가 `marimo==0.24.0`과 필요한 package를 포함하고 `requirements.txt`와 충돌하지 않는다.
3. bootstrap이 저장소 root를 발견하고 정적 local import가 남아 있지 않다.
4. API 키 없이 Snapshot으로 세 페이지가 렌더링된다.
5. `marimo check --strict`, 회귀 테스트와 mobile/desktop smoke test를 통과한다.
6. 위 `/server` 공개 링크에서 import, CSS, Snapshot 접근과 Excel export를 실제로 확인한다.
7. Source URL만 노출되고 secret, 로컬 절대경로와 traceback은 노출되지 않는다.

운영 수준 배포에서는 read-only app 모드(`marimo run`)와 서버 측 secret을 사용하고, Molab 공개 notebook의 접근정책과 데이터 공개 범위를 별도로 검토한다.

공식 참고자료: [Marimo CLI](https://docs.marimo.io/cli/), [Molab](https://docs.marimo.io/guides/molab/), [Inline dependencies](https://docs.marimo.io/guides/package_management/inlining_dependencies/), [WASM 배포](https://docs.marimo.io/guides/wasm/)
