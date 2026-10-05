---
name: run
description: 한국·미국 AI·양자·로봇 밸류체인 주간 분석을 실행합니다. 종목 수익률과 거시 지표를 갱신하고, 새 뉴스를 근거로 태그를 다시 매긴 뒤, 두 인터랙티브 아티팩트를 재게시하고 Gmail 초안까지 만듭니다. "테마 브리핑 돌려줘", "주간 분석 실행", "AI 양자 로봇 업데이트"처럼 요청하거나 주간 루틴이 실행될 때 사용합니다. 인자로 kr, us, all(기본)을 받습니다.
---

# 주간 테마 브리핑 실행

이 스킬은 `data/kr.json`, `data/us.json`을 이번 주 데이터로 갱신하고 페이지와 메일을 다시 만듭니다.
숫자는 손으로 고치지 말고 `scripts/update.py`로 넣습니다. 서술(뉴스 사례, 태그, 국면 진단)만 직접 씁니다.

- 플러그인 루트: 이 파일에서 두 단계 위 폴더 (`plugins/theme-stock-brief/`)
- 데이터를 저장하려면 git 저장소 체크아웃에서 실행해야 합니다. 설치된 플러그인 캐시에서 실행 중이면
  `glorismoon/pyupbit` 저장소의 `claude/ai-quantum-robot-stocks-gilvs5` 브랜치를 체크아웃해 그 안의 `plugins/theme-stock-brief/`에서 작업합니다.
- 인자: `kr`, `us`, `all`(기본). 설정은 `data/config.json` (아티팩트 URL, 브랜치, 메일 제목).
- 먼저 `references/methodology.md`(태그·점수 규칙)와 `references/data-sources.md`(도구별 사용법과 제약)를 읽습니다.

## 0. 도구가 없을 때

- 작업 폴더에 `pyupbit` 저장소가 없으면 `add_repo`(owner `glorismoon`, repo `pyupbit`, access `push`)로 추가하고 안내된 대로 clone 합니다.
- Zacks·FMP·Alpha Vantage 도구가 없으면 WebSearch로 대표 종목(엔비디아·마이크론·아이온큐·테슬라 등)과 미국 10년물 금리만 갱신하고, `meta.asOf`에 "웹 검색 기준"이라고 적습니다. 갱신하지 못한 종목은 그대로 둡니다.
- Gmail 도구가 없으면 초안 대신 `out/email.html` 경로를 보고합니다.
- 어떤 도구가 없었는지는 마지막 보고에 반드시 적습니다.

## 1. 준비

```bash
cd <plugin-root>
git fetch origin claude/ai-quantum-robot-stocks-gilvs5 && git checkout claude/ai-quantum-robot-stocks-gilvs5 && git pull
python3 scripts/build.py check
```

## 2. 미국 종목 수익률 (us)

1. `python3 scripts/update.py tickers us`로 대상 티커를 받습니다.
2. Zacks `compare_stocks`를 5개씩 묶어 호출합니다 (`section: "CREC"`가 가장 짧습니다). 묶음 하나가 실패하면 티커를 나눠 다시 부르고, 끝까지 실패하는 티커(예: QNT, SKHY)는 건너뜁니다.
3. 각 티커에서 다음 값을 뽑아 `metrics.json`(스크래치 폴더)에 씁니다.
   - `px` ← `price.previous_day.close`
   - `ytd` ← `price.percent_chg.ytd`, `w4` ← `price.percent_chg.4_week`, `w1` ← `price.percent_chg.1_week`
   - `rank` ← `zacks_rank.value`
   - `pe` ← `pe.pe_f1` (없으면 `null` → "적자"로 표시), `ps` ← `price.ratio.to_sales`
4. `python3 scripts/update.py apply us metrics.json --as-of "<종가일> 종가 (Zacks, <갱신일> 갱신)"`
5. S&P 500 추정치 타일: 아무 종목의 `ytd`와 `relative_ytd_percent_chg.ytd`로 `(1+ytd/100)/(1+rel/100)-1`을 계산해 `tiles`의 S&P 500 값을 고칩니다.
6. Zacks에 없는 종목(퀀티뉴엄 등)은 WebSearch로 최근 종가를 찾아 해당 회사의 `k.px`와 `p`를 고칩니다.

## 3. 거시 지표 (us, kr 공통)

| 지표 id | 도구 | 넣는 법 |
|---|---|---|
| `ust` | FMP `economics` `treasury-rates` (from=to=최근 영업일) | `update.py set-series <m> ust <월> <year10>` |
| `wti` | Alpha Vantage `WTI` (monthly) | 새 월평균이 나왔을 때만 `set-series <m> wti <월> <값>` |
| `fx` (kr) | Alpha Vantage `FX_MONTHLY` USD→KRW | 월말 또는 최신 종가로 `set-series kr fx <월> <값>` |
| `usd` (us) | Alpha Vantage `FX_MONTHLY` EUR→USD | `set-series us usd <월> <값>` |
| `ff`, `bok` | WebSearch (FOMC·금통위 결과) | 결정이 바뀐 달에만 `set-series` |
| `exp`, `frg`, `capex`, `credit`, `policy` | WebSearch | `stats`, `now`, `nowSub`, `cases`를 직접 고침 |

- 월이 바뀌면 첫 `set-series` 호출에 `--full "2026년 11월"`을 붙입니다. 창은 최근 10개월로 유지되고 이벤트 표시도 함께 밀립니다.
- 시리즈 값을 바꾼 지표는 `now`, `nowSub`, `dir` 문구도 맞춰 고칩니다.
- Alpha Vantage는 하루 25회, 초당 1회 제한이 있습니다. 호출 사이에 간격을 둡니다.

## 4. 뉴스 점검과 사례 갱신

테마·시장별로 지난 7일 뉴스를 WebSearch로 찾습니다. 검색어 예시는 `references/data-sources.md`에 있습니다.
한국 사이트(네이버 금융, 알파스퀘어, 머니투데이, 나무위키 등)는 WebFetch가 막혀 있으니 검색 결과 요약을 근거로 씁니다.

새 사실은 이렇게 반영합니다.
- 해당 단계의 `cases`에 `{d, t, g, s}`를 맨 앞에 추가합니다. `g`는 실제 주가 반응 방향(`up`/`down`), 반응이 엇갈리면 생략합니다.
- 출처는 `sources`에 `키: [라벨, URL]`로 추가하고 `s`에 키를 넣습니다. URL은 검색 결과에 나온 것만 씁니다.
- 회사별 핵심 사실은 해당 회사의 `p`(최대 3줄)를 고칩니다. 날짜를 앞에 붙입니다.
- 단계별 사례는 최신순 4개까지만 두고, 8주가 지난 사례는 지웁니다(구조적 사례는 남겨도 됩니다).
- 뉴스 영향 지도(`heatmap`)의 값은 구조적 판단이라 매주 바꾸지 않습니다. 새 사례가 기존 판단과 반대로 반복될 때만 고치고, 그 행의 `cases`에 근거를 남깁니다.

## 5. 다시 매기기

`references/methodology.md`의 규칙으로 갱신합니다.
1. 거시 지표 `cells` (−3~+3): 지표의 이번 주 방향 × 테마 민감도. 이유 문장도 함께 고칩니다.
2. `regime` 4개: 태그와 한두 문장. 숫자는 이번 주 값으로.
3. `meta.lead`: 한 줄 요약. `<strong>`만 씁니다.
4. `tiles`: kr은 뉴스 수치로 직접, us는 `apply`가 대부분 채웁니다.
5. `calendar`: 지난 일정은 지우고 다음 6주 일정을 넣습니다 (Zacks `fiscal_periods.next_eps_date`).
6. `python3 scripts/update.py touch <m>`

## 6. 빌드와 확인

```bash
python3 scripts/build.py all --email --snapshot
NODE_PATH=$(npm root -g) node scripts/check_render.js kr us
```

검증이나 렌더 확인이 실패하면 고친 뒤 다시 실행합니다. 실패한 채로 게시하지 않습니다.

## 7. 게시

`data/config.json`의 URL로 Artifact를 재게시합니다.
- 이 대화에서 아직 읽거나 게시하지 않은 아티팩트라면 먼저 `Artifact` `action: "read"`로 읽은 뒤 `url`을 지정해 `out/kr.html`, `out/us.html`을 게시합니다.
- `label`에는 "주간 업데이트 <날짜>"를 넣습니다. 아이콘은 넘기지 않습니다.

## 8. 메일 초안

`email` 스킬을 실행합니다 (`skills/email/SKILL.md`). 메일은 보내지 않고 Gmail 초안만 만듭니다.

## 9. 저장과 보고

```bash
git add plugins/theme-stock-brief/data
git commit -m "theme-stock-brief: 주간 데이터 업데이트 <날짜>"
git push -u origin claude/ai-quantum-robot-stocks-gilvs5
```

push가 네트워크 오류로 실패하면 2·4·8·16초 간격으로 최대 4번 다시 시도합니다.
마지막에 사용자에게 한국어 존댓말로 짧게 보고합니다: 테마별 순풍·역풍 점수 변화, 이번 주 상·하위 종목, 새로 반영한 주요 뉴스 3개, 두 아티팩트 링크, Gmail 초안 링크. 실패하거나 건너뛴 단계가 있으면 그대로 적습니다.
