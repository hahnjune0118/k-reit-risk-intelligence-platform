# K-REIT Risk Intelligence Platform

## 1. 프로젝트 개요

본 프로젝트는 상장리츠의 공시자료, 거시경제 지표, 자산별 정보, 공시가격 데이터, Peer 비교 데이터를 연결하여 보유세 부담과 감사위험을 분석하는 Streamlit 기반 리스크 분석 플랫폼입니다.

단순히 DART 공시나 리츠 투자보고서를 조회하는 화면이 아니라, 회계·세무·감사 실무자가 반복적으로 수행하는 자료 수집, 주요 지표 비교, 위험 신호 식별, 요청자료 정리 과정을 하나의 업무 흐름으로 연결하는 것을 목표로 합니다.

현재 공개 버전은 Tax 업무 자동화에 우선순위를 둡니다. 투자추천, 감사의견, 세무신고서, 법률 자문, 정식 가치평가 의견을 제공하지 않으며, 공개 포트폴리오 검토를 위한 예비 분석 도구입니다.

리츠를 분석 대상으로 선택한 이유는 공개자료만으로도 자산, 임대수익, 차입금, 공정가치 평가, 보유세 부담 등 감사·세무 리스크 분석에 필요한 핵심 정보를 구조화할 수 있기 때문입니다. 리츠는 주요 수익이 보유 부동산 임대료에서 발생해 수익 구조를 비교적 명확하게 이해할 수 있고, 상장리츠는 사업보고서와 분기보고서를 통해 주요 분석 기초자료가 공개됩니다.

## 2. 해결하려는 문제

DART, ECOS, V-World, 리츠 공시자료는 모두 유용하지만 실무에서 바로 연결해 보기에는 데이터가 분산되어 있습니다. 특히 리츠를 처음 담당하는 회계·세무 실무자는 다음 작업을 반복해야 합니다.

- 공시자료에서 재무제표, 차입금, 배당, 투자부동산 정보를 찾아 정리
- 금리, 차입금 만기, FFO, NAV, Cap rate, 보유세 부담을 함께 비교
- 동종 리츠 대비 특정 회사의 위험 위치를 파악
- 감사계획 또는 Tax Advisory 초기 단계에서 중점 검토 항목과 요청자료를 정리

이 프로젝트는 이러한 반복 작업을 자동화하여, 검토자가 “어디를 먼저 봐야 하는지” 빠르게 판단할 수 있도록 돕습니다.

## 3. 현재 버전

Current version: **v13 - Tax Review Pack Generator**

v13은 v12의 Tax Red Flag 결과를 실제 Tax Advisory 초기 검토 산출물로 전환하는 버전입니다. 선택한 상장리츠의 보유세 부담, 공시가격 변동, FFO 영향, Peer 비교 결과를 바탕으로 Tax Issue Matrix, 보유세 정합성 검토표, 요청자료 리스트, 검토 메모 초안을 자동 생성합니다.

활성 모드:

1. 일반 정보 및 시나리오
2. Tax: 보유세 분석
3. Assurance: 감사위험 분석
4. 분석 방법론 및 데이터 출처

Deals 모드와 KRX 기반 시장가치 분석은 현재 공개 런타임에서 비활성화되어 있습니다.

## 4. 주요 기능

### 일반 정보 및 시나리오

- 시가총액 순위 Snapshot 기준 분석 대상 리츠 선택
- 선택 회사의 종목코드와 DART corp_code 자동 연결
- 주요 재무·자산 정보 요약
- 거시경제 시나리오와 리스크 요약
- FFO, NAV, Cap rate, 차입금 만기 부담 등 핵심 지표 확인
- 최근 5년 금리와 리츠 주요 지표를 실제 이자율(%)과 금액(억원) 표로 구분 표시

### Peer Benchmark

- 상장리츠 Peer Group 비교
- 선택 회사의 상대적 위험 위치 표시
- Peer 대비 차입부담, 이자비용 부담, 배당 부담, 보유세 부담 비교
- Snapshot 데이터를 사용하여 공개 링크에서도 안정적으로 실행
- 분석 대상회사를 바꾸면 General, Assurance, Tax 화면이 같은 회사 상태로 함께 갱신
- 자산별 상세자료가 부족한 회사는 회사 전체 Snapshot 기반 proxy 지표로 표시

### Assurance: 감사위험 분석

- 투자부동산 공정가치 위험
- 차입금 만기 및 차환 위험
- 이자비용 부담
- 배당 지속가능성
- RMM(중요왜곡표시위험) 관점의 Red Flag
- KAM(핵심감사사항) 후보 검토 신호
- 감사절차 및 요청자료 추천
- 자산별 임차인·Cap rate·만기 wall이 부족한 회사의 회사 단위 proxy 분석

### Tax: 보유세 분석

- 보유세 / FFO
- 보유세 / 영업수익
- 공시가격 / 투자부동산 장부금액
- 보유세 부담 Peer Benchmark
- Tax Issue Matrix
- Holding Tax Reconciliation(보유세 정합성 검토)
- FFO 현금유출 스트레스
- Tax 요청자료 리스트 자동 생성
- Tax Review Memo 초안 다운로드
- 모든 상장리츠에 대해 회사 전체 Snapshot 기반 Tax Review Pack 생성

### 분석 방법론 및 데이터 출처

- 데이터 구조
- Snapshot 기반 설계
- 상장리츠를 분석 대상으로 선택한 이유
- API 보안
- 추정값과 공시값의 구분
- 회사별 상세 자산·보유세 데이터 가용성의 차이
- 한계 및 면책 문구

## 5. 데이터 출처

이 프로젝트는 데이터의 성격을 명확히 구분합니다.

- **DART**: 공시자료 및 재무제표 기반 데이터
- **ECOS**: 기준금리, 국고채, 회사채 등 거시경제 지표
- **V-World / official land price related data**: 공시가격, 개별공시지가, 기준시가 등 보유세 분석 관련 데이터
- **Internal CSV snapshot/sample data**: 공개 배포 환경에서 안정적으로 실행하기 위한 예시 및 기준 데이터
- **Peer benchmark snapshot data**: Peer Benchmark와 Red Flag Engine의 입력 데이터
- **Tax snapshot data**: 자산별 상세자료가 제한된 회사의 Tax Review Pack 생성을 위한 회사 전체 Snapshot 기반 예시 추정 데이터

`source_type = "sample_snapshot"`인 데이터는 공개 포트폴리오 검토용 예시 데이터입니다. 감사된 자료나 공식 확정 자료로 과도하게 해석하지 않도록 UI와 문서에서 구분합니다.

공개 앱은 시작 시 모든 상장리츠의 DART 자료를 실시간 호출하지 않습니다. 사용자가 사이드바에서 분석 대상회사를 선택하면 해당 회사의 Snapshot 기반 최근 5년 흐름을 우선 사용하고, Snapshot이 부족한 경우에만 선택 회사의 DART 자료를 보조적으로 사용할 수 있도록 설계했습니다.

회사별 상세 자산·보유세 데이터의 가용성은 서로 다를 수 있습니다. 상세 데이터가 부족한 회사는 다른 회사의 자산 샘플을 재사용하지 않고, 회사 전체 Snapshot 기반 예시 추정값을 사용해 Tax Review Pack을 생성합니다. 이 값은 신고 목적 세액이 아니라 예비 검토용 입력값입니다.

v13은 `data_availability.py`에서 회사별 데이터 범위를 판정합니다. 자산별 상세 섹션은 선택 회사의 회사별 상세 데이터가 있을 때만 표시하고, 부족한 경우에는 회사 전체 재무 Snapshot과 Peer Benchmark 기반 proxy 표를 표시합니다.

## 6. API Key 및 보안

공개 배포 버전은 서버 측 데이터 연결 설정을 사용하도록 설계되어 있으며, 사용자는 별도의 인증키를 입력할 필요가 없습니다. 실시간 API 호출이 제한될 경우 Snapshot 또는 예시 데이터로 자동 전환됩니다.

보안 원칙:

- API Key는 GitHub 저장소에 저장하지 않습니다.
- API Key는 Streamlit UI에 표시하지 않습니다.
- API Key는 입력 위젯의 기본값으로 주입하지 않습니다.
- 화면, 로그, 디버그 출력에 표시될 가능성이 있는 요청값과 응답값은 마스킹합니다.
- Streamlit Secrets 또는 환경변수를 통해 서버 측에서 인증값을 관리합니다.
- 공개 UI에는 인증값 입력 필드를 표시하지 않습니다.

서버 측 설정 이름:

```toml
ECOS_API_KEY = "..."
DART_API_KEY = "..."
REALTY_PRICE_API_KEY = "..."
```

## 7. 현재 제외된 기능

현재 공개 버전에서는 다음 기능을 비활성화했습니다.

- Deals mode
- KRX market valuation
- KRX 기반 market-implied valuation
- 시장가격 기반 P/NAV, P/FFO 분석
- 거래 목적 가치평가

KRX 기반 시장가치 분석과 Deals 분석은 안정적인 데이터 연결과 별도 업무 흐름이 정리되는 경우 향후 모듈로 재검토할 수 있습니다.

## 8. 실행 방법

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

개발 점검:

```powershell
py -m pip install -r requirements-dev.txt
py -m compileall -q . -x "(\.git|\.venv|venv|__pycache__|\.cache|\.vscode)"
py -m pytest -q
```

선택적 Peer Snapshot 갱신:

```powershell
py scripts\refresh_reit_peer_snapshot.py
```

위 갱신 스크립트는 앱 시작 시 자동 실행되지 않습니다.

## 9. 리뷰 추천 파일

저장소를 빠르게 검토하려면 다음 순서가 좋습니다.

1. [docs/Reviewer_Guide.md](docs/Reviewer_Guide.md): 3분 리뷰 가이드
2. [docs/V13_Feature_Summary.md](docs/V13_Feature_Summary.md): v13 Tax Review Pack 기능 요약
3. [docs/Architecture.md](docs/Architecture.md): 앱 구조와 데이터 흐름
4. [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md): 현재 범위와 향후 방향
5. [CHANGELOG.md](CHANGELOG.md): 버전별 변경 이력

핵심 코드 파일:

- `app.py`: Streamlit 진입점 및 화면 orchestration
- `config.py`: 버전, 화면 라벨, endpoint 상수
- `api_manager.py`: API 인증값 로딩 및 마스킹
- `dart_financials.py`: 분석 대상회사 마스터, 종목코드/DART corp_code 연결, 최근 5년 재무 흐름 로딩
- `calculations_peer.py`: Peer metric 및 percentile 계산
- `data_availability.py`: 회사별 상세 데이터 가용성 및 분석 범위 판정
- `calculations_tax_review_pack.py`: Tax Issue Matrix, 요청자료, 검토 메모 생성
- `tax_data_loader.py`: Tax Snapshot 및 회사별 fallback 데이터 로딩
- `red_flag_engine.py`: Assurance/Tax Red Flag 평가
- `ui_assurance.py`: 감사위험 분석 화면
- `ui_tax.py`: 보유세 분석 화면
- `ui_methodology.py`: 방법론 및 데이터 출처 화면

## 10. 버전 관리

현재 버전은 `v13`입니다. 중요 기능이 추가되는 경우 `v14`, `v15`처럼 순차적으로 올립니다.

버전을 변경할 때는 다음 파일을 함께 맞춥니다.

- `VERSION`
- `CHANGELOG.md`
- `config.py`
