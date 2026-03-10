import streamlit as st
import requests
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(page_title="🏫 학교", page_icon="🏫", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f5f6fa; color: #1a1a2e; }
    html, body, [class*="css"] { color: #1a1a2e; }
    .main .block-container { padding-top: 1rem; }
    .stAlert p { color: #1a1a2e !important; }
    .streamlit-expanderHeader { color: #1a1a2e !important; font-weight: 600; }
    .streamlit-expanderContent { background: #fff; }
    .stSelectbox label { color: #1a1a2e !important; font-weight: 600; }
    h2, h3, h4 { color: #1a1a2e !important; }
</style>
""", unsafe_allow_html=True)

# ── 기본 정보 ────────────────────────────────────────────────
API_KEY            = "ee1619138aef47d7a9a8200b7dbe52b5"
ATPT_OFCDC_SC_CODE = "E10"
SD_SCHUL_CODE      = "7310405"

# ── 날짜 계산: 12시 이후면 내일 기준 ────────────────────────
now        = datetime.now()
after_noon = now.hour >= 12

# 표시 기준 날짜
target_dt     = now + timedelta(days=1) if after_noon else now
target_str    = target_dt.strftime("%Y%m%d")
target_disp   = target_dt.strftime("%Y년 %m월 %d일")
weekday_num   = target_dt.weekday()
weekday_names = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
weekday_kr    = weekday_names[weekday_num]

day_label = "내일" if after_noon else "오늘"

# ── 시간표 JSON 로드 ─────────────────────────────────────────
@st.cache_data
def load_timetable():
    json_path = Path(__file__).parent / "timetable.json"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

timetable_data = load_timetable()

# ── 급식 API ─────────────────────────────────────────────────
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
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        data = res.json()
        if "RESULT" in data:
            return [], None
        rows = data["mealServiceDietInfo"][1]["row"]
        return rows, None
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
        item = item.strip()
        item = re.sub(r"^\d+\.", "", item).strip()
        item = re.sub(r"\(\d+(\.\d+)*\)", "", item).strip()
        item = re.sub(r"\s+", " ", item)
        if item:
            cleaned.append(item)
    return cleaned

# ══════════════════════════════════════════════════════════════
#  헤더
# ══════════════════════════════════════════════════════════════
badge_color = "#fd7272" if after_noon else "#55efc4"
badge_text_color = "#fff" if after_noon else "#1a1a2e"
badge_icon = "🌙 내일 정보" if after_noon else "☀️ 오늘 정보"

st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
        border-radius: 16px; padding: 28px 36px;
        margin-bottom: 24px; color: #eaeaea;
    ">
        <h1 style="margin:0; font-size:2.2rem; color:#ffffff;">🏫 우리 학교 대시보드</h1>
        <p style="margin:8px 0 0; font-size:1.4rem; color:#e0e0e0;">
            📅 {target_disp} &nbsp;|&nbsp; {weekday_kr}
            &nbsp;<span style="background:{badge_color}; color:{badge_text_color};
                border-radius:20px; padding:2px 12px; font-size:.95rem;">{badge_icon}</span>
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════
#  2컬럼 레이아웃
# ══════════════════════════════════════════════════════════════
col_meal, col_tt = st.columns([1, 1], gap="large")

# ── 왼쪽: 급식 ───────────────────────────────────────────────
with col_meal:
    st.markdown(f'<h2 style="color:#1a1a2e;">🍱 급식 ({day_label})</h2>', unsafe_allow_html=True)

    if weekday_num >= 5:
        st.info("급식이 없어요! 🏖️")
    else:
        meal_rows, meal_err = fetch_meal(target_str)

        if meal_err:
            st.warning(meal_err)
        elif not meal_rows:
            st.info("급식이 없어요! 🏖️")
        else:
            for row in meal_rows:
                meal_type = row.get("MMEAL_SC_NM", "급식")
                raw_menu  = row.get("DDISH_NM", "")
                menu_list = parse_menu(raw_menu)
                kcal      = row.get("CAL_INFO", "")

                menu_html = "".join(
                    f'<div style="padding:4px 0; font-size:.97rem; color:#2d3436;">• {m}</div>'
                    for m in menu_list
                )
                kcal_html = f'<p style="margin:10px 0 0; font-size:.85rem; color:#636e72;">🔥 {kcal}</p>' if kcal else ""

                st.markdown(
                    f"""
                    <div style="
                        background:#ffffff; border-left: 5px solid #0f3460;
                        border-radius: 10px; padding: 16px 20px; margin-bottom: 12px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
                    ">
                        <h4 style="margin:0 0 10px; color:#0f3460;">🥢 {meal_type}</h4>
                        {menu_html}{kcal_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ── 오른쪽: 시간표 ───────────────────────────────────────────
with col_tt:
    st.markdown(f'<h2 style="color:#1a1a2e;">📚 시간표 ({day_label})</h2>', unsafe_allow_html=True)

    student_num = st.selectbox(
        "👤 번호를 선택하세요",
        options=list(range(1, 31)),
        format_func=lambda x: f"{x}번",
        index=0,
    )

    subject_colors = {
        "국어": "#e17055", "수학": "#00b894", "영어": "#0984e3",
        "과학": "#6c5ce7", "사회": "#e0a800", "체육": "#fd79a8",
        "음악": "#e67e22", "미술": "#a29bfe", "도덕": "#00cec9",
        "자율": "#636e72", "진로": "#6c757d", "동아리": "#74b9ff",
        "청소": "#fab1a0",
    }

    def render_timetable(day: str, subjects: list, highlight: bool = False) -> str:
        bg     = "#f0f4ff" if highlight else "#ffffff"
        border = "#0f3460" if highlight else "#dee2e6"
        h_color = "#0f3460" if highlight else "#495057"
        label  = f"⭐ {day} (오늘)" if highlight else day

        html = (
            f'<div style="background:{bg}; border:2px solid {border}; '
            f'border-radius:12px; padding:16px; margin-bottom:8px; '
            f'box-shadow:0 2px 8px rgba(0,0,0,0.05);">'
            f'<h4 style="margin:0 0 12px; color:{h_color};">{label}</h4>'
        )
        for i, subj in enumerate(subjects, 1):
            c = subject_colors.get(subj, "#74b9ff")
            html += (
                f'<div style="display:flex; align-items:center; margin-bottom:6px;">'
                f'<span style="min-width:36px; font-size:.8rem; color:#868e96; font-weight:600;">{i}교시</span>'
                f'<span style="background:{c}22; color:{c}; border:1.5px solid {c}; '
                f'border-radius:20px; padding:3px 14px; font-weight:700; font-size:.92rem;">{subj}</span>'
                f'</div>'
            )
        html += "</div>"
        return html

    student_tt = timetable_data.get(str(student_num), {})

    if weekday_num >= 5:
        st.info("주말이라 시간표가 없어요! 🎉")
        for day in ["월요일","화요일","수요일","목요일","금요일"]:
            with st.expander(f"📋 {day}"):
                st.markdown(render_timetable(day, student_tt.get(day, [])), unsafe_allow_html=True)
    else:
        target_day = weekday_names[weekday_num]
        other_days = [d for d in ["월요일","화요일","수요일","목요일","금요일"] if d != target_day]

        st.markdown(render_timetable(target_day, student_tt.get(target_day, []), highlight=True), unsafe_allow_html=True)
        for day in other_days:
            with st.expander(f"📋 {day}"):
                st.markdown(render_timetable(day, student_tt.get(day, [])), unsafe_allow_html=True)

# ── 푸터 ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#aaa; font-size:.82rem;'>"
    "데이터 출처: 나이스(NEIS) 교육정보 개방 포털 · 급식 정보는 매일 자동 갱신됩니다.</p>",
    unsafe_allow_html=True,
)
