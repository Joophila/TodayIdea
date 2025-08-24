# IdeaBrowser‑KR (Full, Static + GPT)

**한국형 IdeaBrowser** 정적 사이트 버전입니다. GitHub Pages로 호스팅하고, GitHub Actions가 매일
- 한국 데이터 소스(네이버 데이터랩/네이버·다음·유튜브)를 수집,
- 점수화·정렬,
- **GPT로 '오늘의 아이디어' 및 각 아이디어의 설명/왜 지금/진입전략/시장 요약을 생성**,
- 결과를 `docs/ideas.json`과 `docs/index.html`에서 보여줍니다.

> 서버 없이 동작하며, API 키는 GitHub Secrets로 관리합니다.

## 빠른 시작

1. 이 리포를 GitHub에 푸시
2. **Settings → Pages**: Branch=`main`, Folder=`/docs`
3. **Settings → Secrets and variables → Actions**에 아래 Secrets 등록
   - `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`
   - `KAKAO_REST_API_KEY`
   - `YOUTUBE_API_KEY`
   - `OPENAI_API_KEY`
4. **Actions** 탭에서 `Update site data` 워크플로 수동 실행(또는 스케줄 대기)

## 파일 구조
```
.github/workflows/update.yml   # 스케줄/수동 실행
tools/update.py                # 데이터 수집 + GPT 요약 + 점수 산출
tools/{keywords.json,config.json}
docs/index.html                # UI
docs/assets/{styles.css,app.js}
docs/ideas.json               # 생성물(JSON)
```

## 설정 포인트
- 키워드/카테고리: `tools/keywords.json`
- 가중치/윈도우/모델: `tools/config.json`
- UI 커스터마이즈: `docs/index.html`, `docs/assets/*`

## 비용/안전
- GitHub Actions 실행 + GPT 토큰 사용에 **비용**이 발생할 수 있습니다. 키워드 수·주기·프롬프트 길이를 줄여 관리하세요.
- 각 API의 이용약관·쿼터 준수 필요.
