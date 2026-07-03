# Reviewer Guide

## 1. 3분 리뷰 순서

이 저장소를 빠르게 검토하려면 다음 순서로 보시면 됩니다.

1. `README.md`에서 프로젝트 목적과 현재 v12 범위를 확인합니다.
2. 앱을 실행하고 사이드바가 `분석 모드 → 분석 대상회사 → 시나리오 → 데이터 연결 상태` 순서로 보이는지 확인합니다.
3. 분석 대상회사가 시가총액 순위 Snapshot 기준으로 정렬되고, 회사를 선택하면 종목코드와 DART corp_code가 자동 표시되는지 확인합니다.
4. `Assurance: 감사위험 분석`에서 Peer 기반 Red Flag와 감사절차 추천을 확인합니다.
5. `Tax: 보유세 분석`에서 보유세 부담 Peer Benchmark와 요청자료 추천을 확인합니다.
6. `docs/Architecture.md`에서 앱 구조와 데이터 흐름을 확인합니다.

## 2. 프로젝트가 보여주는 역량

이 프로젝트는 다음 역량을 보여주기 위한 공개 포트폴리오입니다.

- 회계·세무·감사 업무 흐름을 데이터 제품 구조로 재해석
- DART, ECOS, V-World 등 분산 데이터의 연결 설계
- Streamlit 기반 업무 자동화 앱 구현
- Assurance와 Tax workflow를 위한 Red Flag 자동화
- API Key 비노출 보안 설계
- Snapshot 기반 공개 배포 안정성 확보

## 3. 실행 방법

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

테스트:

```powershell
py -m pip install -r requirements-dev.txt
py -m compileall -q . -x "(\.git|\.venv|venv|__pycache__|\.cache|\.vscode)"
py -m pytest -q
```

## 4. 공개 앱에서 확인할 화면

활성 모드는 정확히 네 가지입니다.

- 일반 정보 및 시나리오
- Assurance: 감사위험 분석
- Tax: 보유세 분석
- 분석 방법론 및 데이터 출처

공개 UI에서는 다음 항목이 보이면 안 됩니다.

- Deals 모드
- KRX API 입력 또는 KRX 연결 상태
- API Key 입력 필드
- 인증값의 전체 또는 일부
- 사이드바의 공시 기준일 선택기
- 별도 종목코드 입력 필드

## 5. v12에서 특히 볼 부분

### Peer Benchmark

`data/reit_peer_snapshot.csv`를 기준으로 선택한 리츠의 차입부담, 이자비용 부담, 배당 부담, 보유세 부담을 Peer Group과 비교합니다.

### 선택 회사 기반 최근 5년 흐름

일반 정보 화면의 `최근 5년 흐름: 금리와 리츠 주요 지표` 표는 금리와 재무지표를 하나의 축으로 섞지 않습니다. 금리는 실제 이자율(%)로, NAV·FFO·총자산·차입금·이자비용은 실제 금액(억원)으로 표시합니다.

### Assurance Red Flag

감사계획 단계에서 중점적으로 봐야 할 위험 신호를 RMM(중요왜곡표시위험) 관점으로 정리하고, 단일 `감사절차 및 요청자료` 표에서 관련 감사절차와 요청자료를 제안합니다.

### Tax Red Flag

보유세 / FFO, 보유세 / 영업수익, 공시가격 / 투자부동산 장부금액 등 Tax 검토 지표를 Peer 대비 비교하고, 단일 `Tax 검토사항 및 요청자료` 표로 검토 포인트를 정리합니다.

## 6. 데이터 해석 시 유의사항

이 앱은 예비 분석 도구입니다. 다음 결론을 직접 제공하지 않습니다.

- 감사의견
- 세무신고 목적의 확정 세액
- 투자추천
- 법률 자문
- 정식 가치평가 의견

Snapshot 또는 예시 데이터는 공개 리뷰 안정성을 위해 포함되어 있으며, 공식 확정 데이터로 과도하게 해석하지 않아야 합니다.

## 7. 주요 파일

- `app.py`: Streamlit 진입점
- `config.py`: 버전과 화면 라벨
- `api_manager.py`: 인증값 로딩 및 마스킹
- `dart_financials.py`: 회사 선택, 종목코드/DART corp_code 연결, 최근 5년 재무 흐름 로딩
- `calculations_peer.py`: Peer Benchmark 계산
- `red_flag_engine.py`: Red Flag 평가
- `ui_assurance.py`: Assurance 화면
- `ui_tax.py`: Tax 화면
- `ui_methodology.py`: 방법론 화면
- `data/reit_peer_snapshot.csv`: Peer Snapshot
- `data/red_flag_rules.json`: Red Flag 규칙
