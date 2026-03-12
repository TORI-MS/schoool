import streamlit as st
import requests
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

st.set_page_config(page_title="🏫 우리 학교 오늘", page_icon="🏫", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #f0f2f8; color: #1a1a2e; }
    html, body, [class*="css"] { color: #1a1a2e; }
    .main .block-container { max-width: 720px; padding: 1rem 1.5rem 3rem; }
    .stAlert p { color: #1a1a2e !important; }
    .streamlit-expanderHeader { color: #1a1a2e !important; font-weight: 600; }
    .stSelectbox label { color: #1a1a2e !important; font-weight: 600; }
    h2, h3, h4 { color: #1a1a2e !important; }
    div[data-testid="stExpander"] { background: #fff; border-radius: 10px; margin-bottom: 6px; }
    div[data-testid="stMarkdownContainer"] { overflow: visible !important; height: auto !important; }
    div[data-testid="stMarkdownContainer"] > div { overflow: visible !important; height: auto !important; }
    .element-container { overflow: visible !important; }
</style>
""", unsafe_allow_html=True)

# ── 기본 정보 ────────────────────────────────────────────────
API_KEY            = "ee1619138aef47d7a9a8200b7dbe52b5"
ATPT_OFCDC_SC_CODE = "E10"
SD_SCHUL_CODE      = "7310405"

# ── 날짜 계산: 오후 1시 이후면 내일 기준 ────────────────────
now       = datetime.now()
show_next = now.hour >= 13
target_dt = now + timedelta(days=1) if show_next else now

target_str  = target_dt.strftime("%Y%m%d")
target_disp = target_dt.strftime("%Y년 %m월 %d일")
weekday_num = target_dt.weekday()
weekday_names = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
weekday_kr  = weekday_names[weekday_num]

is_tomorrow = target_dt.date() != now.date()

# ── 시간표 JSON 로드 (3학년 11반 고정) ───────────────────────
@st.cache_data
def load_timetable():
    p = Path(__file__).parent / "timetable.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

timetable_data = load_timetable()

# ── 급식 API ─────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_meal(date_str: str):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": API_KEY, "Type": "json",
        "pIndex": 1, "pSize": 10,
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "MLSV_YMD": date_str,
    }
    try:
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        data = res.json()
        if "RESULT" in data:
            return [], None
        return data["mealServiceDietInfo"][1]["row"], None
    except requests.exceptions.ConnectionError:
        return [], "🌐 네트워크 연결 실패"
    except requests.exceptions.Timeout:
        return [], "⏱️ 요청 시간 초과"
    except Exception as e:
        return [], f"오류: {e}"

def parse_menu(raw: str) -> list:
    items = re.split(r"<br\s*/>", raw, flags=re.IGNORECASE)
    cleaned = []
    for item in items:
        item = re.sub(r"^\d+\.", "", item).strip()
        item = re.sub(r"\(\d+(\.\d+)*\)", "", item).strip()
        item = re.sub(r"\s+", " ", item)
        if item:
            cleaned.append(item)
    return cleaned

# ── 과목 색상 ─────────────────────────────────────────────────
subject_colors = {
    "화작": "#e17055", "영독": "#0984e3", "스포츠": "#fd79a8",
    "지식재산일반": "#6c5ce7", "윤리와사상": "#f9a825", "미술창작": "#a29bfe",
    "사물인터넷": "#00b894", "진로": "#636e72", "음악3": "#e67e22",
    "미적분": "#d63031", "확통": "#e84393", "물리학Ⅱ": "#6c5ce7",
    "심리학": "#00cec9", "국어": "#e17055", "수학": "#00b894",
    "영어": "#0984e3", "과학": "#6c5ce7", "사회": "#e0a800",
    "체육": "#fd79a8", "음악": "#e67e22", "미술": "#a29bfe",
    "도덕": "#00cec9", "자율": "#636e72", "동아리": "#74b9ff",
    "청소": "#fab1a0",
}

# ══════════════════════════════════════════════════════════════
#  헤더
# ══════════════════════════════════════════════════════════════
tomorrow_badge = (
    ' <span style="background:#fd7272; color:#fff; border-radius:20px; '
    'padding:2px 12px; font-size:.9rem;">내일 미리보기</span>'
    if is_tomorrow else ""
)

st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
    border-radius: 16px; padding: 24px 30px; margin-bottom: 20px; color: #fff;
">
    <h1 style="margin:0; font-size:2rem; color:#fff;">🏫 우리 학교 오늘</h1>
    <p style="margin:6px 0 0; font-size:1.2rem; color:#cdd6f4;">
        📅 {target_disp} &nbsp;|&nbsp; {weekday_kr}{tomorrow_badge}
    </p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  섹션 1 — 급식
# ══════════════════════════════════════════════════════════════
st.markdown('<h2 style="color:#1a1a2e; margin-bottom:8px;">🍱 급식</h2>', unsafe_allow_html=True)

if weekday_num >= 5:
    st.info("주말이라 급식이 없어요! 🏖️")
else:
    meal_rows, meal_err = fetch_meal(target_str)
    if meal_err:
        st.warning(meal_err)
    elif not meal_rows:
        st.info("급식 정보가 없어요! 🏖️")
    else:
        for row in meal_rows:
            meal_type = row.get("MMEAL_SC_NM", "급식")
            menu_list = parse_menu(row.get("DDISH_NM", ""))
            kcal      = row.get("CAL_INFO", "")

            menu_html = "".join(
                f'<div style="padding:3px 0; font-size:.97rem; color:#2d3436;">• {m}</div>'
                for m in menu_list
            )
            extra = (
                f'<span style="background:#fff3cd; color:#856404; border-radius:12px; '
                f'padding:2px 10px; font-size:.82rem;">🔥 {kcal}</span>'
                if kcal else ""
            )
            st.markdown(f"""
<div style="background:#fff; border-radius:12px; padding:18px 22px;
            margin-bottom:10px; box-shadow:0 2px 10px rgba(0,0,0,0.07);
            border-top: 4px solid #0f3460;">
    <div style="font-size:1rem; font-weight:700; color:#0f3460; margin-bottom:10px;">🥢 {meal_type}</div>
    {menu_html}
    <div style="margin-top:10px;">{extra}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  섹션 2 — 시간표 (3학년 11반, 번호 선택)
# ══════════════════════════════════════════════════════════════
st.markdown(
    '<h2 style="color:#1a1a2e; margin-bottom:4px;">📚 시간표</h2>'
    '<p style="color:#888; font-size:.85rem; margin-bottom:12px;">3학년 11반</p>',
    unsafe_allow_html=True
)

student_num = st.selectbox(
    "👤 번호 선택",
    options=list(range(1, 31)),
    format_func=lambda x: f"{x}번",
    index=20,  # 기본값 21번
)

student_tt  = timetable_data.get(str(student_num), {})
has_room    = "교실" in student_tt

# ── 시간표 렌더링 ─────────────────────────────────────────────
def show_day(day: str, highlight: bool = False):
    subs  = student_tt.get(day, [])
    rooms = student_tt.get("교실", {}).get(day, []) if has_room else []

    if not subs:
        return

    bg           = "#eef2ff" if highlight else "#fff"
    border_color = "#0f3460" if highlight else "#dee2e6"
    border_thick = "3px"    if highlight else "1px"
    star         = "⭐ "    if highlight else ""

    # 헤더
    st.markdown(
        f'<div style="background:{bg}; border:{border_thick} solid {border_color}; '
        f'border-radius:12px 12px 0 0; padding:10px 16px;">'
        f'<span style="font-weight:700; color:#0f3460; font-size:.97rem;">{star}{day}</span></div>',
        unsafe_allow_html=True
    )

    # 교시별 행
    for i, subj in enumerate(subs):
        if not subj:
            continue
        room = rooms[i] if i < len(rooms) else ""
        c    = subject_colors.get(subj, "#74b9ff")
        room_tag = f'<span style="font-size:.73rem; color:#999; margin-left:8px;">📍{room}</span>' if room else ""
        st.markdown(
            f'<div style="display:flex; align-items:center; padding:6px 16px; '
            f'background:{bg}; '
            f'border-left:{border_thick} solid {border_color}; '
            f'border-right:{border_thick} solid {border_color}; '
            f'border-bottom:1px solid {"#dce3f5" if highlight else "#f0f0f0"};">'
            f'<span style="min-width:44px; font-size:.8rem; color:#868e96; font-weight:600;">{i+1}교시</span>'
            f'<span style="background:{c}22; color:{c}; border:1.5px solid {c}; '
            f'border-radius:16px; padding:3px 14px; font-weight:700; font-size:.9rem;">{subj}</span>'
            f'{room_tag}</div>',
            unsafe_allow_html=True
        )

    # 하단 마감
    st.markdown(
        f'<div style="background:{bg}; border:{border_thick} solid {border_color}; '
        f'border-top:none; border-radius:0 0 12px 12px; height:10px; margin-bottom:10px;"></div>',
        unsafe_allow_html=True
    )

# 오늘(또는 내일) 강조 카드
if weekday_num >= 5:
    st.info("주말이라 시간표가 없어요! 🎉")
else:
    today_day  = weekday_names[weekday_num]
    other_days = [d for d in ["월요일","화요일","수요일","목요일","금요일"] if d != today_day]

    show_day(today_day, highlight=True)

    # 나머지 요일 expander
    for day in other_days:
        with st.expander(f"📋 {day}"):
            show_day(day)

# ── 푸터 ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#aaa; font-size:.8rem;'>"
    "데이터 출처: 나이스(NEIS) 교육정보 개방 포털</p>",
    unsafe_allow_html=True,
)
