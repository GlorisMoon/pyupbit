# 데이터 출처와 사용법

## 쓸 수 있는 도구 (2026년 10월 기준 확인)

| 데이터 | 도구 | 비고 |
|---|---|---|
| 미국 종목 종가·수익률·Zacks Rank·선행 PER·P/S·실적일 | Zacks `compare_stocks` | 2~10개씩 받지만 지원 안 되는 티커가 하나라도 있으면 묶음 전체가 실패합니다. 5개씩 부르고, 실패하면 나눠서 다시 부릅니다. QNT, SKHY는 미지원 |
| 미국 국채금리 | FMP `economics` `treasury-rates` | 무료 플랜에서 동작. 날짜를 좁게(from=to) 주면 응답이 짧습니다 |
| 미국 대형주 일별 종가 | FMP `chart` `historical-price-eod-light` | 일부 대형주만. ETF·소형주·한국 종목은 플랜 제한 |
| 원/달러, 유로/달러 | Alpha Vantage `FX_MONTHLY` | 하루 25회, 초당 1회 제한 |
| WTI | Alpha Vantage `WTI` (monthly) | 전 기간이 오니 최근 값만 씁니다 |
| 뉴스·한국 종목 주가 | WebSearch | 한국 사이트는 WebFetch가 막혀 있어 검색 결과 요약을 근거로 씁니다 |

쓰지 못하는 것: FMP `quote`·`forex`·`commodity`(플랜 제한), Financial Datasets(크레딧 없음), 네이버 금융·KRX·알파스퀘어·나무위키 직접 조회(네트워크 차단).

## 필드 매핑 (Zacks → `update.py apply`)

| metrics 키 | Zacks 필드 |
|---|---|
| `px` | `price.previous_day.close` |
| `ytd` | `price.percent_chg.ytd` |
| `w4` | `price.percent_chg.4_week` |
| `w1` | `price.percent_chg.1_week` |
| `rank` | `zacks_rank.value` |
| `pe` | `pe.pe_f1` (없으면 null) |
| `ps` | `price.ratio.to_sales` |

S&P 500 연초 대비 추정: `(1 + ytd/100) / (1 + price.relative_ytd_percent_chg.ytd/100) − 1`.

## 주간 뉴스 검색어 예시

미국
- `Nvidia AMD Broadcom stock news this week`
- `Micron SanDisk memory prices HBM week`
- `Vertiv GE Vernova Constellation data center power stock`
- `Oracle CoreWeave AI data center debt financing`
- `IonQ Rigetti D-Wave Quantinuum stock news`
- `Tesla Optimus humanoid robot news`, `Intuitive Surgical Symbotic stock`
- `Fed FOMC decision`, `10-year Treasury yield week`

한국
- `SK하이닉스 삼성전자 주가 이번주 HBM`
- `한미반도체 이수페타시스 삼성전기 주가`
- `HD현대일렉트릭 LS일렉트릭 효성중공업 주가`
- `양자 관련주 우리로 케이씨에스 드림시큐리티`
- `로봇주 레인보우로보틱스 두산로보틱스 로보티즈 주가`
- `코스피 외국인 순매도 주간`, `원달러 환율 주간 마감`, `한국은행 금통위`
- 매월 1일: `수출입 동향 반도체 수출`

## 알려진 함정
- 허니웰(HON)은 사업 분할 영향으로 연초 대비 수익률이 왜곡됩니다. 비교 문장에 쓰지 않습니다.
- 검색 결과 요약의 날짜가 섞여 나올 때가 있습니다. 숫자는 기사 날짜를 확인하고, 다른 출처의 숫자와 충돌하면 Zacks 숫자를 우선합니다.
- 서비스나우 등은 주식 분할로 주가 단위가 바뀌었을 수 있습니다. 수익률은 Zacks 값을 그대로 씁니다.
