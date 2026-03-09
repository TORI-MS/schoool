import streamlit as st
import requests
import re
from datetime import datetime

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(page_title="🏫 우리 학교 오늘", page_icon="🏫", layout="wide")

# ── 기본 정보 ────────────────────────────────────────────────
API_KEY          = "ee1619138aef47d7a9a8200b7dbe52b5"
ATPT_OFCDC_SC_CODE = "E10"
SD_SCHUL_CODE    = "7310405"

# ── 날짜 / 요일 ──────────────────────────────────────────────
today      = datetime.today()
today_str  = today.strftime("%Y%m%d")          # YYYYMMDD
today_disp = today.strftime("%Y년 %m월 %d일")
weekday_num = today.weekday()                   # 0=월 … 6=일
weekday_names = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
weekday_kr    = weekday_names[weekday_num]

# ── 시간표 데이터 ─────────────────────────────────────────────
timetable = {
    "월요일": ["국어", "수학", "영어", "과학", "체육", "음악"],
    "화요일": ["수학", "사회", "국어", "미술", "영어", "도덕"],
    "수요일": ["영어", "국어", "수학", "체육", "과학", "자율"],
    "목요일": ["과학", "영어", "사회", "수학", "국어", "진로"],
    "금요일": ["체육", "수학", "국어", "영어", "동아리", "청소"],
}

# ── 급식 API 호출 ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_meal(date_str: str):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 10,
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "MLSV_YMD": date_str,
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        rows = data["mealServiceDietInfo"][1]["row"]
        return rows
    except Exception:
        return []

def parse_menu(raw: str) -> list[str]:
    """요리번호(숫자.숫자. 형태) 제거 후 메뉴 리스트 반환"""
    items = raw.split("<br/>")
    cleaned = []
    for item in items:
        item = re.sub(r"[\d]+\.", "", item).strip()
        item = re.sub(r"\s+", " ", item)
        if item:
            cleaned.append(item)
    return cleaned

# ══════════════════════════════════════════════════════════════
#  헤더
# ══════════════════════════════════════════════════════════════
st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 28px 36px;
        margin-bottom: 24px;
        color: white;
    ">
        <h1 style="margin:0; font-size:2.4rem;">🏫 우리 학교 오늘</h1>
        <p style="margin:8px 0 0; font-size:1.5rem; opacity:.9;">
            📅 {today_disp} &nbsp;|&nbsp; {weekday_kr}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════
#  2컬럼 레이아웃
# ══════════════════════════════════════════════════════════════
col_meal, col_tt = st.columns([1, 1], gap="large")

# ── 왼쪽: 오늘의 급식 ─────────────────────────────────────────
with col_meal:
    st.markdown("## 🍱 오늘의 급식")

    if weekday_num >= 5:   # 주말
        st.info("오늘은 급식이 없어요! 🏖️")
    else:
        meal_rows = fetch_meal(today_str)
        if not meal_rows:
            st.info("오늘은 급식이 없어요! 🏖️")
        else:
            for row in meal_rows:
                meal_type = row.get("MMEAL_SC_NM", "급식")
                raw_menu  = row.get("DDISH_NM", "")
                menu_list = parse_menu(raw_menu)
                kcal      = row.get("CAL_INFO", "")

                st.markdown(
                    f"""
                    <div style="
                        background:#f0f9ff;
                        border-left: 5px solid #667eea;
                        border-radius: 10px;
                        padding: 16px 20px;
                        margin-bottom: 12px;
                    ">
                        <h4 style="margin:0 0 10px; color:#667eea;">🥢 {meal_type}</h4>
                        {"".join(f'<div style="padding:3px 0; font-size:.97rem;">• {m}</div>' for m in menu_list)}
                        {"<p style='margin:10px 0 0; font-size:.85rem; color:#888;'>🔥 " + kcal + "</p>" if kcal else ""}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ── 오른쪽: 오늘의 시간표 ────────────────────────────────────
with col_tt:
    st.markdown("## 📚 오늘의 시간표")

    subject_colors = {
        "국어": "#FF6B6B", "수학": "#4ECDC4", "영어": "#45B7D1",
        "과학": "#96CEB4", "사회": "#FFEAA7", "체육": "#DDA0DD",
        "음악": "#F0A500", "미술": "#FF8A65", "도덕": "#A8E6CF",
        "자율": "#B0BEC5", "진로": "#CE93D8", "동아리": "#80DEEA",
        "청소": "#EF9A9A",
    }

    def render_timetable(day: str, highlight: bool = False):
        subjects = timetable.get(day, [])
        bg = "#f8f4ff" if highlight else "#fafafa"
        border = "#764ba2" if highlight else "#ddd"
        html = f'<div style="background:{bg}; border:2px solid {border}; border-radius:12px; padding:16px; margin-bottom:8px;">'
        if highlight:
            html += f'<h4 style="margin:0 0 12px; color:#764ba2;">⭐ {day} (오늘)</h4>'
        else:
            html += f'<h4 style="margin:0 0 12px; color:#555;">{day}</h4>'
        for i, subj in enumerate(subjects, 1):
            color = subject_colors.get(subj, "#90CAF9")
            html += (
                f'<div style="display:flex; align-items:center; margin-bottom:6px;">'
                f'<span style="min-width:28px; font-size:.8rem; color:#999;">{i}교시</span>'
                f'<span style="background:{color}33; color:{color}; border:1px solid {color}; '
                f'border-radius:20px; padding:2px 12px; font-weight:600;">{subj}</span>'
                f'</div>'
            )
        html += "</div>"
        return html

    # 오늘 요일 (주말이면 그냥 안내)
    if weekday_num >= 5:
        st.info("오늘은 주말이라 시간표가 없어요! 🎉")
        for day in ["월요일","화요일","수요일","목요일","금요일"]:
            with st.expander(f"📋 {day} 시간표"):
                st.markdown(render_timetable(day), unsafe_allow_html=True)
    else:
        today_day = weekday_names[weekday_num]

        # 오늘 시간표 — 강조 박스
        st.markdown(render_timetable(today_day, highlight=True), unsafe_allow_html=True)

        # 나머지 요일 — expander
        other_days = [d for d in ["월요일","화요일","수요일","목요일","금요일"] if d != today_day]
        for day in other_days:
            with st.expander(f"📋 {day} 시간표"):
                st.markdown(render_timetable(day), unsafe_allow_html=True)

# ── 푸터 ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#aaa; font-size:.82rem;'>"
    "데이터 출처: 나이스(NEIS) 교육정보 개방 포털 · 급식 정보는 매일 자동 갱신됩니다.</p>",
    unsafe_allow_html=True,
)
