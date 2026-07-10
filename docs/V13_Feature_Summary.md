# v13 Feature Summary

## v13 - Tax Review Pack Generator

v13은 v12의 Tax Red Flag 결과를 실제 Tax Advisory 초기 검토 산출물로 전환하는 버전입니다. 선택한 상장리츠의 보유세 부담, 공시가격 변동, FFO 영향, Peer 비교 결과를 바탕으로 Tax Issue Matrix, 보유세 정합성 검토표, 요청자료 리스트, 검토 메모 초안을 자동 생성합니다.

## 1. Tax 중심 UI

공개 모드는 다음 순서로 정리했습니다.

1. 일반 정보 및 시나리오
2. Tax: 보유세 분석
3. Assurance: 감사위험 분석
4. 분석 방법론 및 데이터 출처

Assurance 기능은 유지하지만, v13의 개발 초점은 Tax mode입니다.

## 2. Tax Issue Matrix

Tax Issue Matrix는 Peer 기반 Red Flag와 보유세 정합성, FFO 현금유출 스트레스를 하나의 실무 검토 표로 변환합니다.

주요 컬럼:

- 세무 이슈
- 위험수준
- 발생 근거
- 영향받는 지표
- 검토 방향
- 요청자료
- 업무유형
- 데이터 기준

위험수준은 `높음`, `주의`, `정상`, `데이터 부족`으로 표시합니다.

## 3. Holding Tax Reconciliation

보유세 정합성 검토표는 회계상 투자부동산 장부가액과 공시가격, 추정 과세표준, 추정 보유세를 연결합니다.

자산별 상세 데이터가 부족한 회사는 `회사 전체 추정` 행으로 표시하며, `source_type = peer_snapshot_estimate`를 사용합니다. 이 값은 신고 목적 세액이 아니라 공개자료 및 Snapshot 기반 예비 검토용 추정값입니다.

## 4. Tax Request List Generator

Tax Issue Matrix 결과를 기반으로 요청자료 리스트를 자동 생성합니다.

기본 요청자료 예시:

- 재산세 고지서
- 토지대장
- 건축물대장
- 개별공시지가 조회자료
- 자산별 장부가액 명세
- 임대수익 명세
- FFO 산정자료
- 취득 관련 계약서
- 자산별 위치 및 면적 자료

## 5. Tax Review Memo Draft

선택 회사, Tax Issue Matrix, 보유세 정합성 검토, 요청자료 리스트를 바탕으로 한국어 Markdown 메모 초안을 생성합니다. 화면에서 바로 검토할 수 있고 `Tax Review Memo 다운로드` 버튼으로 `.md` 파일을 받을 수 있습니다.

메모는 다음 구조를 따릅니다.

1. 검토 대상
2. 주요 검토 결과
3. 추가 검토 필요사항
4. 요청자료
5. 제한 및 유의사항

Memo의 `제한 및 유의사항` 섹션은 항상 포함됩니다. 이 섹션은 Tax Review Memo가 세무신고 목적의 확정 세액 산출이나 법률의견이 아니라 공개자료 및 Snapshot 기반의 예비 검토 초안임을 명시합니다. `source_type`에 estimate 또는 sample 성격이 포함되면 회사 전체 Snapshot 기반 추정값을 사용했다는 추가 문구를 포함합니다.

## 6. FFO 현금유출 스트레스

보유세 증가율과 FFO 스트레스 가정을 사용해 추가 현금유출과 보유세 / FFO 부담을 계산합니다. Tax mode 상단의 `Tax 분석 가정` 패널에서 주요 가정을 조정할 수 있습니다.

## 7. 데이터 및 한계

사용 데이터:

- DART 및 공시자료 기반 재무 Snapshot
- ECOS 거시경제 지표
- V-World / 공시가격 관련 데이터
- `data/reit_peer_snapshot.csv`
- `data/reit_tax_snapshot.csv`
- 내부 CSV 및 예시 데이터

## 8. 회사 단위 fallback 구조

v13은 SK리츠와 같이 일부 상세 sample이 있는 회사에만 자산별 상세 섹션을 표시합니다. 다른 상장리츠는 SK리츠의 자산 목록, 임차인, Cap rate, 차입금 만기 자료를 재사용하지 않습니다.

자산별 상세자료가 부족한 회사도 다음 산출물은 회사 전체 Snapshot과 Peer Benchmark를 사용해 생성합니다.

- Tax Summary
- Tax Issue Matrix
- Holding Tax Reconciliation
- 요청자료 리스트
- FFO 현금유출 스트레스
- Tax Review Memo 초안
- Assurance 회사 단위 proxy 표

화면 상단의 데이터 범위 배너와 Tax 데이터 기준 expander는 `source_type`, `source_note`, 데이터 기준연도, 자산별 보유세·임차인·차입금 만기·Cap rate 상세 가용성을 함께 표시합니다.

본 기능은 세무신고 목적의 확정 세액 산출, 법률의견, 공식 세무자문을 제공하지 않습니다. 최종 판단에는 원자료 확인과 전문가 검토가 필요합니다.
