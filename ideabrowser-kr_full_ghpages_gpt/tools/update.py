from __future__ import annotations
import os, json, time, datetime as dt
import requests
from typing import Any, Dict, List

# === Secrets (Actions → Secrets) ===
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID","")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET","")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY","")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY","")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")

# ---- Data sources ----
def naver_datalab(keyword_group:str, keywords:List[str], start_date:str, end_date:str, time_unit:str='date'):
    url = "https://openapi.naver.com/v1/datalab/search"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET, "Content-Type": "application/json"}
    body = {"startDate":start_date, "endDate":end_date, "timeUnit":time_unit, "keywordGroups":[{"groupName":keyword_group, "keywords":keywords}]}
    r = requests.post(url, headers=headers, json=body, timeout=30); r.raise_for_status(); return r.json()

def naver_news(query:str, display:int=20, sort:str="date"):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query":query, "display":display, "sort":sort}
    r = requests.get(url, headers=headers, params=params, timeout=30); r.raise_for_status(); return r.json()

def naver_blog(query:str, display:int=20, sort:str="date"):
    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query":query, "display":display, "sort":sort}
    r = requests.get(url, headers=headers, params=params, timeout=30); r.raise_for_status(); return r.json()

def naver_cafe(query:str, display:int=20, sort:str="date"):
    url = "https://openapi.naver.com/v1/search/cafearticle.json"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    params = {"query":query, "display":display, "sort":sort}
    r = requests.get(url, headers=headers, params=params, timeout=30); r.raise_for_status(); return r.json()

def kakao_blog(query:str, page:int=1, size:int=10):
    url = "https://dapi.kakao.com/v2/search/blog"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query":query, "page":page, "size":size, "sort":"recency"}
    r = requests.get(url, headers=headers, params=params, timeout=30); r.raise_for_status(); return r.json()

def kakao_cafe(query:str, page:int=1, size:int=10):
    url = "https://dapi.kakao.com/v2/search/cafe"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query":query, "page":page, "size":size, "sort":"recency"}
    r = requests.get(url, headers=headers, params=params, timeout=30); r.raise_for_status(); return r.json()

def yt_trending_kr(max_results:int=25):
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part":"snippet,statistics","chart":"mostPopular","regionCode":"KR","maxResults":max_results,"key":YOUTUBE_API_KEY}
    r = requests.get(url, params=params, timeout=30); r.raise_for_status(); return r.json()

# ---- Scoring ----
def compute_score(agg:Dict[str,float], weights:Dict[str,float]):
    norm = {k: max(0.0, min(1.0, agg.get(k,0.0)/100.0)) for k in weights}
    total = sum(weights[k]*norm[k] for k in weights)
    return {"total": round(total*100.0,2), "breakdown": {k: round(norm[k]*100.0,2) for k in norm}}

# ---- GPT ----
def call_gpt(model:str, sys_prompt:str, user_prompt:str)->str:
    if not OPENAI_API_KEY:
        return "알 수 없습니다 (OPENAI_API_KEY 미설정)"
    try:
        import openai
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role":"system","content":sys_prompt},
                {"role":"user","content":user_prompt}
            ],
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"알 수 없습니다 (GPT 오류: {e})"

def build_prompt_kor(idea:Dict[str,Any])->str:
    # Sources list to pass into GPT to encourage grounded outputs
    sources = idea.get("sources", [])
    sources_txt = "\n".join([f"- {s.get('title','')} ({s.get('publisher','')}) {s.get('url','')}" for s in sources[:8]])
    trend_tip = ""
    if idea.get("trend_series"):
        last = idea["trend_series"][-1]; first = idea["trend_series"][0]
        trend_tip = f"검색지수: 시작 {first['value']} → 최근 {last['value']} (기간 {first['date']} ~ {last['date']})"
    community_counts = idea.get("community_counts", {})
    comm_tip = ", ".join([f"{k}:{v}" for k,v in community_counts.items()])
    template = f'''
요구사항:
1) **한줄 요약**(최대 30자)
2) **설명**(2~3문장, 근거 중심)
3) **왜 지금(Why now)**(데이터/정책/행태 변화 기반, 근거 없으면 "근거가 부족합니다")
4) **진입 전략(GTM)**(채널/메시지/초기니치, 3~5개 불릿)
5) **시장 요약**(TAM/SAM/SOM 추정 기준 또는 유사 카테고리 지표, 근거 없으면 "확실하지 않음")
6) **리스크/규제**(데이터 기반 or "확실하지 않음")
7) **검증 단계(Validation)**(실험 3~5개, KPI 포함)

반드시 다음 원칙을 지키세요:
- 출처가 없으면 단정하지 말고 "근거가 부족합니다" 또는 "확실하지 않음"을 명시
- 한국 시장 맥락 중심, 과장 금지, 수치가 필요하면 근거 제시

[아이디어]
- 제목: {idea.get("title","")}
- 카테고리: {idea.get("category","")}
- 태그: {", ".join(idea.get("tags",[]))}
- 점수: {idea.get("score",{}).get("total","")}
- 커뮤니티 신호(건수): {comm_tip}
- {trend_tip}

[주요 출처 후보]
{sources_txt}

요구 형식(JSON):
{{
  "one_liner": "...",
  "summary": "...",
  "why_now": "...",
  "gtm_tactics": ["...", "..."],
  "market": "...",
  "risks": "...",
  "validation_steps": ["...", "..."]
}}
'''
    return template

# ---- Main ----
def main():
    here = os.path.dirname(__file__)
    with open(os.path.join(here,"keywords.json"),"r",encoding="utf-8") as f:
        kws = json.load(f)["entries"]
    with open(os.path.join(here,"config.json"),"r",encoding="utf-8") as f:
        cfg = json.load(f)
    weights = cfg["weights"]; days = int(cfg.get("days","30")); model = cfg.get("model","gpt-4o-mini")

    end = dt.date.today(); start = end - dt.timedelta(days=days)
    sd, ed = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    ideas = []
    for entry in kws[:int(cfg.get("max_ideas_per_run", 8))]:
        kg = entry["keyword_group"]; tags = entry.get("tags",[]); cat = entry.get("category","generic")
        # --- Collect ---
        trend_series = []
        try:
            t = naver_datalab(kg, entry["keywords"], sd, ed, "date")
            for row in t.get("results",[{}])[0].get("data",[]):
                trend_series.append({"date": row.get("period",""), "value": float(row.get("ratio",0.0))})
        except Exception as e:
            pass
        news = []; sources = []
        try:
            n = naver_news(kg, display=10, sort="date")
            for it in n.get("items",[]):
                url = it.get("link"); title = it.get("title","")
                news.append({"url": url, "title": title}); sources.append({"url":url,"title":title,"publisher":"Naver News"})
        except Exception:
            pass
        community_counts = {}
        community_top = []
        try:
            nb = naver_blog(kg, display=5, sort="date").get("items",[])
            nc = naver_cafe(kg, display=5, sort="date").get("items",[])
            kb = kakao_blog(kg, page=1, size=5).get("documents",[])
            kc = kakao_cafe(kg, page=1, size=5).get("documents",[])
            community_counts = {
                "naver_blog": len(nb), "naver_cafe": len(nc),
                "daum_blog": len(kb), "daum_cafe": len(kc)
            }
            for it in nb[:2]:
                community_top.append({"title": it.get("title",""), "url": it.get("link",""), "source":"Naver Blog"})
            for it in kb[:2]:
                community_top.append({"title": it.get("title",""), "url": it.get("url",""), "source":"Daum Blog"})
            for it in nc[:1]:
                community_top.append({"title": it.get("title",""), "url": it.get("link",""), "source":"Naver Cafe"})
            for it in kc[:1]:
                community_top.append({"title": it.get("title",""), "url": it.get("url",""), "source":"Daum Cafe"})
            for it in (kb[:2]+kc[:2]):
                sources.append({"url": it.get("url",""), "title": it.get("title",""), "publisher":"Daum"})
        except Exception:
            pass
        video_pop = 0.0
        try:
            yt = yt_trending_kr(25)
            video_pop = float(min(len(yt.get("items",[])),100))
        except Exception:
            pass

        agg = {"trend": (trend_series[-1]["value"] if trend_series else 0.0),
               "community": sum(community_counts.values()),
               "news": len(news), "video": video_pop, "regulatory_invert": 50.0}
        score = compute_score(agg, weights)

        idea = {
            "title": kg, "keyword_group": kg, "category": cat, "tags": tags,
            "score": score, "trend_series": trend_series,
            "community_counts": community_counts, "community_top": community_top,
            "sources": sources
        }

        # --- GPT summarize ---
        sys_prompt = "너는 한국 시장에 특화된 객관적인 리서치 보조자다. 출처 없는 추측은 금지하고, 근거 부족은 명시한다."
        user_prompt = build_prompt_kor(idea)
        txt = call_gpt(model, sys_prompt, user_prompt)
        try:
            j = json.loads(txt)
        except Exception:
            j = {"one_liner": "알 수 없습니다", "summary": txt[:400] if txt else "알 수 없습니다",
                 "why_now":"확실하지 않음","gtm_tactics":[],"market":"확실하지 않음",
                 "risks":"확실하지 않음","validation_steps":[]}
        idea.update(j)
        ideas.append(idea)
        time.sleep(0.2)

    data = {"generated_at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ideas": sorted(ideas, key=lambda x: x["score"]["total"], reverse=True)}
    docs = os.path.abspath(os.path.join(here,"..","docs"))
    os.makedirs(docs, exist_ok=True)
    with open(os.path.join(docs,"ideas.json"),"w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
