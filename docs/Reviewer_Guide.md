# Reviewer Guide

## 1. 3분 리뷰 순서

이 저장소를 빠르게 검토하려면 다음 순서로 보시면 됩니다.

1. `README.md`에서 프로젝트 목적과 현재 v13 범위를 확인합니다.
2. 앱을 실행하고 사이드바가 `분석 모드 → 분석 대상회사 → 시나리오 → 데이터 연결 상태` 순서로 보이는지 확인합니다.
3. 분석 대상회사가 시가총액 순위 Snapshot 기준으로 정렬되고, 회사를 선택하면 종목코드와 DART corp_code가 자동 표시되는지 확인합니다.
4. 분석 대상회사를 바꾼 뒤 `분석 실행`을 누르면 General, Assurance, Tax 화면 상단의 `현재 분석 대상`이 함께 바뀌는지 확인합니다.
5. `Tax: 보유세 분석`에서 Tax Issue Matrix, 보유세 정합성 검토, 요청자료 리스트, Tax Review Memo 초안을 확인합니다.
6. `Assurance: 감사위험 분석`에서 Peer 기반 Red Flag와 감사절차 추천을 확인합니다.
7. `docs/Architecture.md`에서 앱 구조와 데이터 흐름을 확인합니다.

## 2. 프로젝트가 보여주는 역량

이 프로젝트는 다음 역량을 보여주기 위한 공개 포트폴리오입니다.

- 회계·세무·감사 업무 흐름을 데이터 제품 구조로 재해석
- DART, ECOS, V-World 등 분산 데이터의 연결 설계
- Streamlit 기반 업무 자동화 앱 구현
- Tax workflow를 위한 Review Pack 자동화
- Assurance workflow를 위한 Red Flag 자동화
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
- Tax: 보유세 분석
- Assurance: 감사위험 분석
- 분석 방법론 및 데이터 출처

공개 UI에서는 다음 항목이 보이면 안 됩니다.

- Deals 모드
- KRX API 입력 또는 KRX 연결 상태
- API Key 입력 필드
- 인증값의 전체 또는 일부
- 사이드바의 공시 기준일 선택기
- 별도 종목코드 입력 필드

## 5. v13에서 특히 볼 부분

### Tax Review Pack

v13은 Tax mode를 중심으로 Tax Red Flag 결과를 실무 산출물로 전환합니다. 선택 회사의 보유세 부담, 공시가격/장부가액 관계, FFO 현금유출 스트레스, Peer 비교 결과를 바탕으로 다음 산출물을 만듭니다.

- Tax Issue Matrix
- 보유세 정합성 검토
- 요청자료 리스트
- Tax Review Memo 초안

SK리츠 외 회사도 `data/reit_tax_snapshot.csv`와 Peer Snapshot 기반 예시 추정값으로 Tax Pack이 표시됩니다. 이 경우 화면에는 Snapshot 기반 추정이라는 데이터 기준이 표시되어야 합니다.

비-SK 리츠를 선택했을 때 정상적으로 보여야 하는 항목:

- Tax Summary
- Tax Issue Matrix
- 보유세 정합성 검토의 `회사 전체 추정` 행
- 요청자료 리스트
- FFO 현금유출 스트레스
- Tax Review Memo 초안
- 공시가격 자료 출처의 `source_type`과 `source_note`
- Assurance의 회사 단위 자산·임차인 proxy, 차입금 만기·차환 proxy, 가치·NAV proxy 표

비-SK 리츠 화면에는 SK리츠의 자산명, 임차인명, Cap rate, 차입금 만기 상세가 표시되면 안 됩니다.

### Peer Benchmark

`data/reit_peer_snapshot.csv`를 기준으로 선택한 리츠의 차입부담, 이자비용 부담, 배당 부담, 보유세 부담을 Peer Group과 비교합니다.

### 선택 회사 기반 최근 5년 흐름

일반 정보 화면의 `최근 5년 흐름: 금리와 리츠 주요 지표` 표는 금리와 재무지표를 하나의 축으로 섞지 않습니다. 금리는 실제 이자율(%)로, NAV·FFO·총자산·차입금·이자비용은 실제 금액(억원)으로 표시합니다.

### 회사 변경 후 화면 갱신

사이드바에서 분석 대상회사를 변경하고 `분석 실행`을 누르면 공통 상태가 갱신됩니다. 상세 자산·보유세 데이터가 부족한 회사는 다른 회사의 샘플 자산을 보여 주지 않고, 데이터 부족 안내와 함께 Peer Benchmark 및 재무 Snapshot 중심으로 표시합니다.

### Assurance Red Flag

감사계획 단계에서 중점적으로 봐야 할 위험 신호를 RMM(중요왜곡표시위험) 관점으로 정리하고, 단일 `감사절차 및 요청자료` 표에서 관련 감사절차와 요청자료를 제안합니다.

### Tax Red Flag

보유세 / FFO, 보유세 / 영업수익, 공시가격 / 투자부동산 장부금액 등 Tax 검토 지표를 Peer 대비 비교하고, `Tax 검토사항 및 요청자료` 표와 `Tax Issue Matrix`로 검토 포인트를 정리합니다.

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
- `data_availability.py`: 회사별 상세 데이터 가용성 및 fallback 범위 판정
- `calculations_tax_review_pack.py`: Tax Review Pack 산출물 생성
- `tax_data_loader.py`: Tax Snapshot 및 fallback 데이터 로딩
- `red_flag_engine.py`: Red Flag 평가
- `ui_assurance.py`: Assurance 화면
- `ui_tax.py`: Tax 화면
- `ui_methodology.py`: 방법론 화면
- `data/reit_peer_snapshot.csv`: Peer Snapshot
- `data/red_flag_rules.json`: Red Flag 규칙
