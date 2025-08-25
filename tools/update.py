
from __future__ import annotations
import os, json, time, math, datetime, re as dt, requests
from typing import Any, Dict, List

NAVER_CLIENT_ID=os.getenv("NAVER_CLIENT_ID",""); NAVER_CLIENT_SECRET=os.getenv("NAVER_CLIENT_SECRET","")
KAKAO_REST_API_KEY=os.getenv("KAKAO_REST_API_KEY",""); YOUTUBE_API_KEY=os.getenv("YOUTUBE_API_KEY","")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY","")
REDDIT_CLIENT_ID=os.getenv("REDDIT_CLIENT_ID",""); REDDIT_CLIENT_SECRET=os.getenv("REDDIT_CLIENT_SECRET",""); REDDIT_USER_AGENT=os.getenv("REDDIT_USER_AGENT","IdeaBrowserKR/1.0")
GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY",""); GOOGLE_CSE_ID=os.getenv("GOOGLE_CSE_ID","")

HERE=os.path.dirname(__file__)
CFG=json.load(open(os.path.join(HERE,"config.json"),"r",encoding="utf-8"))
FILTERS=json.load(open(os.path.join(HERE,"filters.json"),"r",encoding="utf-8"))
KWS=json.load(open(os.path.join(HERE,"keywords.json"),"r",encoding="utf-8"))["entries"]
TRUST=CFG.get("trust_coeff",{}); CAPS=CFG.get("caps",{})

def _contains_any(t, arr): t=(t or "").lower(); return any(k.lower() in t for k in arr)
def _is_politics_or_ent(text): return _contains_any(text,FILTERS.get("politics_keywords",[])) or _contains_any(text,FILTERS.get("entertainment_keywords",[]))
def _is_generic(term, series, gdoms):
    term=(term or "").strip().lower()
    if len(term)<=FILTERS.get("generic_length_threshold",2): return True
    if term in [s.lower() for s in FILTERS.get("stopwords_ko",[])+FILTERS.get("stopwords_en",[])]: return True
    vals=[p.get("value",0.0) for p in (series or [])]
    if len(vals)>=5:
        mu=sum(vals)/len(vals); sigma=(sum((v-mu)**2 for v in vals)/len(vals))**0.5
        if sigma<FILTERS.get("trend_volatility_sigma_min",3.0): return True
    if gdoms and len(set(gdoms))<FILTERS.get("google_domain_diversity_min",3): return True
    return False
def try_parse_json(text: str):
    if not text:
        return None
    s = text.strip()
    # 코드펜스 제거
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\n|```$", "", s, flags=re.M)
    # 본문에서 첫 JSON 블록 추출
    m = re.search(r"\{.*\}", s, re.S)
    if m:
        blk = m.group(0)
        try:
            return json.loads(blk)
        except Exception:
            return None
    return None

def naver_datalab(kg, keywords, sd, ed):
    try:
        r=requests.post("https://openapi.naver.com/v1/datalab/search",
            headers={"X-Naver-Client-Id":NAVER_CLIENT_ID,"X-Naver-Client-Secret":NAVER_CLIENT_SECRET,"Content-Type":"application/json"},
            json={"startDate":sd,"endDate":ed,"timeUnit":"date","keywordGroups":[{"groupName":kg,"keywords":keywords}]}, timeout=30)
        r.raise_for_status(); return r.json()
    except Exception as e: return {"_error":str(e)}

def naver_search(ep, q, display=20, sort="date"):
    try:
        r=requests.get(f"https://openapi.naver.com/v1/search/{ep}.json",
            headers={"X-Naver-Client-Id":NAVER_CLIENT_ID,"X-Naver-Client-Secret":NAVER_CLIENT_SECRET},
            params={"query":q,"display":display,"sort":sort}, timeout=30)
        r.raise_for_status(); return r.json()
    except Exception as e: return {"_error":str(e)}

def kakao_search(ep, q, page=1, size=10):
    try:
        r=requests.get(f"https://dapi.kakao.com/v2/search/{ep}", headers={"Authorization":f"KakaoAK {KAKAO_REST_API_KEY}"},
                       params={"query":q,"page":page,"size":size,"sort":"recency"}, timeout=30)
        r.raise_for_status(); return r.json()
    except Exception as e: return {"_error":str(e)}

def yt_trending_kr(n=25):
    try:
        r=requests.get("https://www.googleapis.com/youtube/v3/videos",
            params={"part":"snippet,statistics","chart":"mostPopular","regionCode":"KR","maxResults":n,"key":YOUTUBE_API_KEY}, timeout=30)
        r.raise_for_status(); return r.json()
    except Exception as e: return {"_error":str(e)}

def reddit_search(q, limit=8):
    if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET): return []
    try:
        tok=requests.post("https://www.reddit.com/api/v1/access_token",
                          auth=requests.auth.HTTPBasicAuth(REDDIT_CLIENT_ID,REDDIT_CLIENT_SECRET),
                          data={'grant_type':'client_credentials'}, headers={'User-Agent':REDDIT_USER_AGENT}, timeout=20)
        tok.raise_for_status(); token=tok.json().get('access_token')
        r=requests.get("https://oauth.reddit.com/search", headers={'Authorization':f"bearer {token}",'User-Agent':REDDIT_USER_AGENT},
                       params={'q':q,'limit':limit,'sort':'new','t':'month','restrict_sr':False}, timeout=20)
        r.raise_for_status(); out=[]
        for ch in r.json().get('data',{}).get('children',[]):
            d=ch.get('data',{}); sub=(d.get('subreddit','') or '').lower()
            if sub in [s.lower() for s in FILTERS.get('blocked_subreddits',[])]: continue
            title=d.get('title',''); 
            if _is_politics_or_ent(title): continue
            out.append({'title':title,'url':'https://www.reddit.com'+d.get('permalink',''),'source':'Reddit','subreddit':sub})
        return out
    except Exception: return []

def google_search(q, num=8):
    if not (GOOGLE_API_KEY and GOOGLE_CSE_ID): return []
    try:
        r=requests.get("https://www.googleapis.com/customsearch/v1", params={'key':GOOGLE_API_KEY,'cx':GOOGLE_CSE_ID,'q':q,'num':min(num,10)}, timeout=30)
        r.raise_for_status(); out=[]
        for it in r.json().get('items',[]):
            title=it.get('title',''); link=it.get('link','')
            if any(dom in (link or '') for dom in FILTERS.get('blocked_domains',[])): continue
            if _is_politics_or_ent(title): continue
            out.append({'title':title,'url':link,'source':'Google','date':it.get('pagemap',{}).get('metatags',[{}])[0].get('article:published_time','')})
        return out
    except Exception: return []

def scale_cap(v, cap): 
    if cap<=0: return 0.0
    x=max(0.0,min(v,cap)); return (x/cap)*100.0

def compute_score(agg, weights):
    tot=sum(weights[k]*max(0.0,min(1.0,(agg.get(k,0.0)/100.0))) for k in weights)
    return {"total":round(tot*100.0,2),"breakdown":{k:round(max(0.0,min(1.0,(agg.get(k,0.0)/100.0)))*100.0,2) for k in weights}}

def call_gpt(model, sys_prompt, user_prompt):
    if not OPENAI_API_KEY: return "알 수 없습니다 (OPENAI_API_KEY 미설정)"
    try:
        from openai import OpenAI; client=OpenAI(api_key=OPENAI_API_KEY)
        resp=client.chat.completions.create(model=model, messages=[{"role":"system","content":sys_prompt},{"role":"user","content":user_prompt}], temperature=0.2)
        return resp.choices[0].message.content.strip()
    except Exception as e: return f"알 수 없습니다 (GPT 오류: {e})"

def build_prompt(idea):
    ev = idea.get("evidence", [])
    ev_lines = []
    for i, e in enumerate(ev, start=1):
        ev_lines.append(f"[{i}] {e.get('title','')} ({e.get('publisher','')}, {e.get('date','')}) {e.get('url','')}")
    ev_text = "\n".join(ev_lines[:12])

    metrics = idea.get("metrics", {})
    return f"""
역할: 한국 시장 리서치 에디터. 모든 주장/숫자는 Evidence 번호로 근거. 근거 없으면 문장 안에 '근거가 부족합니다/확실하지 않음' 명시.

입력 지표: 검색지수 최근 {metrics.get('trend_last')}, 7일 {metrics.get('trend_delta_7')}%, 30일 {metrics.get('trend_delta_30')}%, σ {metrics.get('trend_sigma')}, 커뮤니티(가중) {metrics.get('community_weighted')}, 뉴스(가중) {metrics.get('news_weighted')}

Evidence:
{ev_text}

아이디어: {idea.get('title','')} / 카테고리: {idea.get('category','')} / 태그: {', '.join(idea.get('tags',[]))}
점수: {idea.get('score',{}).get('total','')}

JSON만:
{{"one_liner":"최대 30자. 과장 금지.","summary":"2~4문장. 각 사실 뒤 [번호].","why_now":"정책/행태/기술 변화. 근거 없으면 '근거가 부족합니다'.","gtm_tactics":["..."],"market":"...","risks":"...","validation_steps":["..."]}}
"""

def compute_metrics(series, comm_w, news_w):
    vals=[p.get('value',0.0) for p in series]
    if vals:
        last=vals[-1]; prev7=vals[-7] if len(vals)>=7 else vals[0]; prev30=vals[0] if len(vals)>=30 else vals[0]
        mu=sum(vals)/len(vals); sigma=(sum((v-mu)**2 for v in vals)/len(vals))**0.5
    else:
        last=prev7=prev30=sigma=0.0
    def pct(a,b): 
        try:
            if b==0: return None
            return round((a-b)/b*100.0,2)
        except: return None
    return {"trend_last":round(last,2),"trend_delta_7":pct(last,prev7),"trend_delta_30":pct(last,prev30),"trend_sigma":round(sigma,2),
            "community_weighted":round(comm_w,2),"news_weighted":round(news_w,2)}

def main():
    weights=CFG["weights"]; days=int(CFG.get("days","30"))
    now_kst=dt.datetime.utcnow()+dt.timedelta(hours=9)
    sd=(now_kst-dt.timedelta(days=days)).date().strftime("%Y-%m-%d"); ed=now_kst.date().strftime("%Y-%m-%d")

    ideas=[]
    for entry in KWS[:int(CFG.get("max_ideas_per_run",10))]:
        kg=entry["keyword_group"]; tags=entry.get("tags",[]); cat=entry.get("category","generic")
        # Trend
        series=[]; t=naver_datalab(kg, entry["keywords"], sd, ed)
        if "results" in t:
            for row in t.get("results",[{}])[0].get("data",[]):
                try: series.append({"date":row.get("period",""),"value":float(row.get("ratio",0.0))})
                except: pass
        # Searches
        sources=[]; evidence=[]; comm_top=[]
        nnews=naver_search("news", kg, 20, "date"); news_items=nnews.get("items",[]) if isinstance(nnews,dict) else []
        for it in news_items[:8]:
            rec={"url":it.get("link",""),"title":it.get("title",""),"publisher":"Naver News","date":it.get("pubDate","")}
            sources.append(rec); evidence.append(rec)
        nb=naver_search("blog", kg, 10, "date").get("items",[])
        nc=naver_search("cafearticle", kg, 10, "date").get("items",[])
        kb=kakao_search("blog", kg, 1, 10).get("documents",[])
        kc=kakao_search("cafe", kg, 1, 10).get("documents",[])
        for it in nb[:2]: comm_top.append({"title":it.get("title",""),"url":it.get("link",""),"source":"Naver Blog"})
        for it in nc[:1]: comm_top.append({"title":it.get("title",""),"url":it.get("link",""),"source":"Naver Cafe"})
        for it in kb[:2]: comm_top.append({"title":it.get("title",""),"url":it.get("url",""),"source":"Daum Blog"})
        for it in kc[:1]: comm_top.append({"title":it.get("title",""),"url":it.get("url",""),"source":"Daum Cafe"})
        goog=google_search(kg,8); redd=reddit_search(kg,8)
        comm_top += [{'title':x['title'],'url':x['url'],'source':x.get('source','Google')} for x in goog[:3]]
        comm_top += [{'title':x['title'],'url':x['url'],'source':f"r/{x.get('subreddit','')}"} for x in redd[:3]]
        for it in goog[:6]:
            rec={"url":it.get("url",""),"title":it.get("title",""),"publisher":"Google","date":it.get("date","")}
            sources.append(rec); evidence.append(rec)
        for it in redd[:6]:
            rec={"url":it.get("url",""),"title":it.get("title",""),"publisher":"Reddit","date":""}
            sources.append(rec); evidence.append(rec)
        gdoms=[x['url'].split('/')[2] for x in goog] if goog else []
        if _is_generic(kg, series, gdoms) or _is_politics_or_ent(kg): continue
        yt=yt_trending_kr(25); video_pop=float(min(len(yt.get("items",[])) if isinstance(yt,dict) else 0, 100))
        raw_comm=TRUST.get("naver_blog",0.85)*len(nb)+TRUST.get("naver_cafe",0.75)*len(nc)+TRUST.get("daum_blog",0.8)*len(kb)+TRUST.get("daum_cafe",0.75)*len(kc)+TRUST.get("reddit",0.6)*len(redd)+TRUST.get("google",0.75)*len(goog)
        raw_news=TRUST.get("naver_news",1.0)*len(news_items); raw_video=TRUST.get("youtube",0.6)*video_pop
        community=scale_cap(raw_comm, CAPS.get("community_max_raw",60)); news=scale_cap(raw_news, CAPS.get("news_max_raw",60)); video=scale_cap(raw_video, CAPS.get("video_max_raw",100))
        trend_last=series[-1]["value"] if series else 0.0; trend=max(0.0, min(100.0, trend_last*TRUST.get("naver_datalab",1.0)))
        agg={"trend":trend,"community":community,"news":news,"video":video,"regulatory_invert":50.0}; score=compute_score(agg, CFG["weights"])
        metrics=compute_metrics(series, raw_comm, raw_news)
        idea={"title":kg,"keyword_group":kg,"category":cat,"tags":tags,"score":score,"trend_series":series,"community_top":comm_top,"sources":sources,"evidence":evidence,"metrics":metrics}
        sys="너는 한국 시장 리서치 에디터. 각 사실/수치 뒤 [번호]로 근거. 근거 없으면 문장 내 표기."
        prompt=build_prompt(idea); out=call_gpt(CFG.get("model","gpt-4o-mini"), sys, prompt)
        try: j=json.loads(out)
        except Exception: j={"one_liner":"알 수 없습니다","summary":out[:500] if out else "알 수 없습니다","why_now":"확실하지 않음","gtm_tactics":[],"market":"확실하지 않음","risks":"확실하지 않음","validation_steps":[]}
        idea.update(j); ideas.append(idea); time.sleep(0.2)

    ideas=sorted(ideas, key=lambda x: x["score"]["total"], reverse=True)
    data={"generated_at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), "ideas": ideas}
    docs=os.path.abspath(os.path.join(HERE,"..","docs")); os.makedirs(docs, exist_ok=True)
    with open(os.path.join(docs,"ideas.json"),"w",encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

if __name__=="__main__": main()
