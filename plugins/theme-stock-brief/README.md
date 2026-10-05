# theme-stock-brief

한국·미국 AI·양자·로봇 밸류체인을 매주 분석해 인터랙티브 아티팩트 두 개를 갱신하고, Gmail 초안을 만드는 Claude Code 플러그인입니다.

## 구성

| 경로 | 내용 |
|---|---|
| `skills/run/SKILL.md` | 주간 분석 전체 절차 (`/theme-stock-brief:run [kr|us|all]`) |
| `skills/email/SKILL.md` | Gmail 초안 작성 (`/theme-stock-brief:email`) |
| `data/kr.json`, `data/us.json` | 밸류체인·기업·뉴스·거시 지표·영향 지도 데이터 |
| `data/config.json` | 아티팩트 URL, 브랜치, 루틴 일정, 메일 제목 |
| `data/history/` | 주간 스냅샷 |
| `assets/template.html` | 두 시장이 함께 쓰는 페이지 템플릿 |
| `scripts/build.py` | 검증, 페이지·메일 생성, 스냅샷 |
| `scripts/update.py` | 종목 수익률·거시 시리즈를 JSON에 반영 |
| `scripts/check_render.js` | 헤드리스 브라우저로 렌더 오류 확인 |
| `references/` | 태그·점수 규칙, 데이터 출처와 제약 |

## 바로 실행

```bash
# 이 저장소에서 플러그인을 바로 불러오기
claude --plugin-dir plugins/theme-stock-brief
# 세션 안에서
/theme-stock-brief:run all
```

마켓플레이스로 설치하려면 저장소 루트의 `.claude-plugin/marketplace.json`을 씁니다.

```bash
claude plugin marketplace add glorismoon/pyupbit
claude plugin install theme-stock-brief@glorismoon-tools
```

(마켓플레이스는 저장소 기본 브랜치에서 읽습니다. 이 브랜치가 병합되기 전에는 `--plugin-dir`를 쓰세요.)

## 수동 빌드

```bash
cd plugins/theme-stock-brief
python3 scripts/build.py check          # 데이터 검증
python3 scripts/build.py all --email    # out/kr.html, out/us.html, out/email.html
```

## 주간 루틴

claude.ai의 Routine으로 매주 월요일 06:49(서울)에 새 세션이 이 브랜치를 받아 `skills/run/SKILL.md`를 실행합니다.
같은 루틴은 언제든 즉시 실행할 수 있습니다.

## 면책

공개 데이터와 뉴스를 정리한 분석 도구이며 투자 권유가 아닙니다.
