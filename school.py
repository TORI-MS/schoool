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

    /* 마크다운 HTML 컨테이너 높이 제한 해제 */
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
now        = datetime.now()
show_next  = now.hour >= 13
target_dt  = now + timedelta(days=1) if show_next else now

target_str  = target_dt.strftime("%Y%m%d")
target_disp = target_dt.strftime("%Y년 %m월 %d일")
weekday_num = target_dt.weekday()
weekday_names = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
weekday_kr  = weekday_names[weekday_num]

today_date  = now.date()
is_tomorrow = (target_dt.date() != today_date)

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

# ── 시간표 API ────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_timetable(date_str: str, grade: int, class_nm: int):
    """
    NEIS 고등학교 시간표 API (hisTimetable)
    반환: (rows: list[dict], error: str | None)
    각 row 예시: {"PERIO": "1", "ITM_NM": "화작", ...}
    """
    url = "https://open.neis.go.kr/hub/hisTimetable"
    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "ALL_TI_YMD": date_str,
        "GRADE": str(grade),
        "CLASS_NM": str(class_nm),
    }
    try:
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        data = res.json()
        if "RESULT" in data:
            # INFO-200: 데이터 없음 (주말/공휴일 등)
            return [], None
        rows = data["hisTimetable"][1]["row"]
        # 교시(PERIO) 순 정렬
        rows.sort(key=lambda r: int(r.get("PERIO", 0)))
        return rows, None
    except requests.exceptions.ConnectionError:
        return [], "🌐 네트워크 연결 실패"
    except requests.exceptions.Timeout:
        return [], "⏱️ 요청 시간 초과"
    except Exception as e:
        return [], f"오류: {e}"

# ── 과목 색상 매핑 ─────────────────────────────────────────────
subject_colors = {
    # 21번 실제 과목
    "화작": "#e17055", "영독": "#0984e3", "스포츠": "#fd79a8",
    "지식재산일반": "#6c5ce7", "윤리와사상": "#fdcb6e", "미술창작": "#a29bfe",
    "사물인터넷": "#00b894", "진로": "#636e72", "음악3": "#e67e22",
    "미적분": "#d63031", "확통": "#e84393", "물리학Ⅱ": "#6c5ce7",
    "심리학": "#00cec9",
    # 공통 과목
    "국어": "#e17055", "수학": "#00b894", "영어": "#0984e3",
    "과학": "#6c5ce7", "사회": "#e0a800", "체육": "#fd79a8",
    "음악": "#e67e22", "미술": "#a29bfe", "도덕": "#00cec9",
    "자율": "#636e72", "동아리": "#74b9ff", "청소": "#fab1a0",
    "한국사": "#e0a800", "통합사회": "#fdcb6e", "통합과학": "#a29bfe",
    "생명과학": "#00b894", "화학": "#e84393", "지구과학": "#0984e3",
    "물리학": "#6c5ce7", "경제": "#e17055", "정치": "#fd79a8",
    "정보": "#00cec9", "기술가정": "#fab1a0",
}

def get_subject_color(itm_nm: str) -> str:
    """
    과목명 완전일치 → 부분일치 순으로 색상 탐색.
    없으면 기본색 반환.
    """
    if not itm_nm:
        return "#74b9ff"
    # 1) 완전 일치
    if itm_nm in subject_colors:
        return subject_colors[itm_nm]
    # 2) 부분 일치 (API 과목명이 더 길거나 짧은 경우 대비)
    for key, color in subject_colors.items():
        if key in itm_nm or itm_nm in key:
            return color
    return "#74b9ff"

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
            extra = ""
            if kcal:
                extra = f'<span style="background:#fff3cd; color:#856404; border-radius:12px; padding:2px 10px; font-size:.82rem;">🔥 {kcal}</span>'

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
#  섹션 2 — 시간표
# ══════════════════════════════════════════════════════════════
st.markdown('<h2 style="color:#1a1a2e; margin-bottom:8px;">📚 시간표</h2>', unsafe_allow_html=True)

# 학년 / 반 선택
col_g, col_c = st.columns(2)
with col_g:
    grade = st.selectbox("🎓 학년", options=[1, 2, 3], format_func=lambda x: f"{x}학년")
with col_c:
    class_nm = st.selectbox("🚪 반", options=list(range(1, 13)), format_func=lambda x: f"{x}반")

# ── 시간표 렌더링 함수 ────────────────────────────────────────
def show_timetable_from_api(date_str: str, grade: int, class_nm: int, highlight: bool = True):
    """API에서 받아온 시간표를 교시별 카드로 렌더링"""
    if weekday_num >= 5:
        st.info("주말이라 시간표가 없어요! 🎉")
        return

    rows, err = fetch_timetable(date_str, grade, class_nm)

    if err:
        st.warning(err)
        return
    if not rows:
        st.info("📭 시간표 정보가 없습니다. (공휴일이거나 아직 등록되지 않았어요)")
        return

    day_label = weekday_kr
    bg           = "#eef2ff" if highlight else "#fff"
    border_color = "#0f3460" if highlight else "#e0e0e0"
    border_thick = "3px" if highlight else "1px"
    star         = "⭐ " if highlight else ""

    # 카드 헤더
    st.markdown(
        f'<div style="background:{bg}; border:{border_thick} solid {border_color}; '
        f'border-radius:12px 12px 0 0; padding:12px 16px; margin-bottom:0;">'
        f'<span style="font-weight:700; color:#0f3460; font-size:1rem;">'
        f'{star}{grade}학년 {class_nm}반 · {day_label}</span></div>',
        unsafe_allow_html=True
    )

    # 교시별 행
    for row in rows:
        perio   = row.get("PERIO", "?")
        itm_nm  = row.get("ITM_NM", "").strip()
        if not itm_nm:
            continue
        c = get_subject_color(itm_nm)
        st.markdown(
            f'<div style="display:flex; align-items:center; padding:6px 16px; '
            f'background:{bg}; border-left:{border_thick} solid {border_color}; '
            f'border-right:{border_thick} solid {border_color}; border-bottom:1px solid #f0f0f0;">'
            f'<span style="min-width:44px; font-size:.8rem; color:#868e96; font-weight:600;">{perio}교시</span>'
            f'<span style="background:{c}22; color:{c}; border:1.5px solid {c}; '
            f'border-radius:16px; padding:3px 14px; font-weight:700; font-size:.9rem;">{itm_nm}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    # 카드 하단 마감선
    st.markdown(
        f'<div style="background:{bg}; border:{border_thick} solid {border_color}; '
        f'border-top:none; border-radius:0 0 12px 12px; height:10px; margin-bottom:10px;"></div>',
        unsafe_allow_html=True
    )

# 오늘(또는 내일) 시간표 — 강조 카드
show_timetable_from_api(target_str, grade, class_nm, highlight=True)

# 이번 주 다른 날 시간표 — expander
if weekday_num < 5:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#555; font-size:.9rem; font-weight:600; margin-bottom:4px;">📅 이번 주 다른 날 시간표</p>',
        unsafe_allow_html=True
    )
    # 이번 주 월~금 날짜 계산
    monday = target_dt - timedelta(days=weekday_num)
    other_days_info = [
        (monday + timedelta(days=i), weekday_names[i])
        for i in range(5)
        if i != weekday_num
    ]

    for dt, day_name in other_days_info:
        with st.expander(f"📋 {day_name} ({dt.strftime('%m/%d')})"):
            rows, err = fetch_timetable(dt.strftime("%Y%m%d"), grade, class_nm)
            if err:
                st.warning(err)
            elif not rows:
                st.info("시간표 정보가 없습니다.")
            else:
                for row in rows:
                    perio  = row.get("PERIO", "?")
                    itm_nm = row.get("ITM_NM", "").strip()
                    if not itm_nm:
                        continue
                    c = get_subject_color(itm_nm)
                    st.markdown(
                        f'<div style="display:flex; align-items:center; padding:5px 8px; margin-bottom:4px;">'
                        f'<span style="min-width:44px; font-size:.8rem; color:#868e96; font-weight:600;">{perio}교시</span>'
                        f'<span style="background:{c}22; color:{c}; border:1.5px solid {c}; '
                        f'border-radius:16px; padding:3px 14px; font-weight:700; font-size:.9rem;">{itm_nm}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

# ── 푸터 ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#aaa; font-size:.8rem;'>"
    "데이터 출처: 나이스(NEIS) 교육정보 개방 포털</p>",
    unsafe_allow_html=True,
)
