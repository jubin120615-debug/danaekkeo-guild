import streamlit as st
import pandas as pd
from datetime import datetime
import cv2
import easyocr
import numpy as np

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Secrets에서 정보 로드
creds_dict = st.secrets["gcp_service_account"]

# 구글 인증
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
client = gspread.authorize(creds)

# 시트 열기 (본인의 시트 이름으로 변경하세요)
sheet = client.open('길드명부').sheet1

# 1. 페이지 설정 (사이드바 항상 노출 고정)
st.set_page_config(page_title="다내꺼 길드 관제 센터", layout="wide", initial_sidebar_state="expanded")

# 2. 세션 상태 초기화
if "current_menu" not in st.session_state:
    st.session_state.current_menu = "공지사항"

if "auth_target" not in st.session_state:
    st.session_state.auth_target = None  # 'admin' 또는 'config' 또는 None

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# 마스터 환경설정 데이터
if "admin_password" not in st.session_state:
    st.session_state.admin_password = "1336"

if "discord_url" not in st.session_state:
    st.session_state.discord_url = "https://discord.com/"

if "kakao_url" not in st.session_state:
    st.session_state.kakao_url = "https://open.kakao.com/"

# 게시판 및 게임 데이터 기본값
if "notices" not in st.session_state:
    st.session_state.notices = [
        {"id": 1, "유형": "🚫 통제", "내용": "제로서버 주요 보스 구역 및 심연 3층은 전부 '다내꺼' 통제 구역입니다.", "날짜": "2026-06-13 09:00"}
    ]

if "headers" not in st.session_state:
    st.session_state.headers = {"col1": "캐릭터명", "col2": "클래스", "col3": "레벨", "col4": "전투력", "col5": "비고"}

if "boss_list" not in st.session_state:
    st.session_state.boss_list = ["벨루치 (필드)", "가나비슈 (필드)", "바포메트 (심연)", "라돈 (심연)", "기타 정예"]

if "guild_members" not in st.session_state:
    try:
        # 구글 시트에서 전체 데이터를 리스트로 가져옴
        data = sheet.get_all_records()
        if data:
            st.session_state.guild_members = pd.DataFrame(data)
        else:
            # 시트가 비어있을 경우 초기 데이터 사용
            st.session_state.guild_members = pd.DataFrame([
                {"캐릭터명": "다내꺼마스터", "클래스": "버서커", "레벨": 75, "전투력": 65400, "비고": "총군"}
            ])
    except Exception as e:
        st.error(f"구글 시트 로드 실패: {e}")
        st.session_state.guild_members = pd.DataFrame([{"캐릭터명": "에러발생", "클래스": "-", "레벨": 0, "전투력": 0, "비고": "-"}])
    ])

if "boss_attendance" not in st.session_state:
    st.session_state.boss_attendance = {
        "다내꺼마스터": 42, "아가사": 38, "전투토끼": 15, "태양5_K세이지": 22, "타양5_K스님": 19, "타양5_Kangnam": 31, "타양5_K땡벌": 8
    }

if "raid_logs" not in st.session_state:
    st.session_state.raid_logs = [
        {"날짜": "2026-06-12", "보스명": "벨루치 (필드)", "참여명단": ["다내꺼마스터", "아가사", "전투토끼", "태양5_K세이지", "타양5_Kangnam"]},
        {"날짜": "2026-06-11", "보스명": "바포메트 (심연)", "참여명단": ["다내꺼마스터", "아가사", "타양5_K스님", "타양5_Kangnam"]}
    ]

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['ko', 'en'], gpu=False)

# 3. 🎨 스타일 가이드 CSS (★사이드바 스크롤바 삭제 및 초슬림 패딩 반영★)
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #121212 !important;
        color: #e0e0e0 !important;
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    
    /* 사이드바 자체 스크롤 완전 박멸 및 88px 락킹 */
    [data-testid="stSidebar"] {
        min-width: 88px !important;
        max-width: 88px !important;
        background-color: #1a1a1a !important;
        border-right: 1px solid #2d2d2d !important;
        overflow: hidden !important;
    }
    
    /* 내부 컨테이너 스크롤 감추기 및 최적 여백 */
    [data-testid="stSidebarUserContent"] {
        padding-top: 10px !important;
        padding-left: 0px !important;
        padding-right: 0px !important;
        display: flex !important;
        flex-direction: column !important;
        overflow: hidden !important;
    }
    
    [data-testid="stSidebarUserContent"] .element-container {
        width: 100% !important;
        display: flex;
        justify-content: center;
    }

    /* 버튼 간격을 촘촘하게 줄여 스크롤 유발 억제 */
    [data-testid="stSidebarUserContent"] div.stButton > button {
        width: 54px !important;
        height: 54px !important;
        border-radius: 14px !important;
        background-color: #232428 !important;
        border: 1px solid #2d3035 !important;
        color: #aaaaaa !important;
        font-size: 1.9rem !important; 
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease !important;
        margin: 3px auto !important;
        padding: 0 !important;
    }
    
    [data-testid="stSidebarUserContent"] div.stButton > button:hover {
        border-color: #00e676 !important;
        color: #00e676 !important;
        background-color: #2b2d32 !important;
    }

    .sidebar-divider {
        width: 30px;
        height: 1px;
        background-color: #2d2d2d;
        margin: 8px auto;
    }

    .auth-box {
        background-color: #1a1a1a;
        border: 1px solid #333333;
        border-radius: 16px;
        padding: 40px;
        max-width: 500px;
        margin: 80px auto;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    }

    .notice-card {
        background-color: #1e1e1e;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #2d2d2d;
        margin-bottom: 16px;
    }
    .badge {
        background-color: #2d2d2d;
        color: #00e676;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: bold;
        margin-right: 12px;
    }
    .stat-card {
        background-color: #1a1a1a;
        border: 1px solid #2d2d2d;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .stat-number {
        color: #00e676;
        font-size: 2rem;
        font-weight: bold;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 🧭 4. 사이드바 영역
# ==========================================
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; width: 100%;">
        <div style="width: 54px; height: 54px; background: linear-gradient(135deg, #00e676, #00b0ff); 
                    border-radius: 14px; display: inline-flex; align-items: center; justify-content: center; 
                    font-weight: bold; color: #121212; font-size: 0.85rem; margin-bottom: 6px;
                    box-shadow: 0 4px 12px rgba(0, 230, 118, 0.35);">
            다내꺼
        </div>
        <div class="sidebar-divider"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # 1층: 기본 메뉴 그룹
    if st.button("📢", help="공지사항", key="side_m1"):
        st.session_state.current_menu = "공지사항"
        st.session_state.auth_target = None
        st.rerun()
        
    if st.button("👥", help="길드원 명부", key="side_m2"):
        st.session_state.current_menu = "명부"
        st.session_state.auth_target = None
        st.rerun()
        
    if st.button("📊", help="보스 참여율 정산", key="side_m3"):
        st.session_state.current_menu = "참여율"
        st.session_state.auth_target = None
        st.rerun()
        
    if st.button("📜", help="레이드 기록 로그", key="side_m4"):
        st.session_state.current_menu = "로그"
        st.session_state.auth_target = None
        st.rerun()

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # 2층: 외부 링크 아웃 커넥터
    if st.button("🎮", help="디스코드 채널 접속", key="link_discord"):
        st.markdown(f'<meta http-equiv="refresh" content="0; url={st.session_state.discord_url}">', unsafe_allow_html=True)
        
    if st.button("💬", help="카카오톡방 접속", key="link_kakao"):
        st.markdown(f'<meta http-equiv="refresh" content="0; url={st.session_state.kakao_url}">', unsafe_allow_html=True)

    # 3층: [분리 구동] 🔑 관리자 모드 활성화 / ⚙️ 시스템 설정
    if st.button("🔑", help="간부 관리자 모드 활성화", key="side_admin_mode"):
        if st.session_state.is_admin:
            st.session_state.is_admin = False
            st.toast("🛡️ 관리자 권한이 안전하게 해제되었습니다.")
        else:
            st.session_state.auth_target = "admin"
        st.rerun()
        
    if st.button("⚙️", help="마스터 환경설정 진입", key="side_config_mode"):
        st.session_state.auth_target = "config"
        st.rerun()

    # 사이드바 아이콘 선택 액티브 광채 디자인 매핑 코드
    if st.session_state.auth_target == "admin":
        st.markdown("""<style>[data-testid="stSidebarUserContent"] div.stButton:nth-child(9) > button { border-color: #00e676 !important; color: #00e676 !important; background-color: rgba(0, 230, 118, 0.15) !important; box-shadow: 0 0 12px rgba(0, 230, 118, 0.4) !important; }</style>""", unsafe_allow_html=True)
    elif st.session_state.auth_target == "config" or st.session_state.current_menu == "환경설정":
        st.markdown("""<style>[data-testid="stSidebarUserContent"] div.stButton:nth-child(10) > button { border-color: #00e676 !important; color: #00e676 !important; background-color: rgba(0, 230, 118, 0.15) !important; box-shadow: 0 0 12px rgba(0, 230, 118, 0.4) !important; }</style>""", unsafe_allow_html=True)
    elif st.session_state.is_admin:
        st.markdown("""<style>[data-testid="stSidebarUserContent"] div.stButton:nth-child(9) > button { border-color: #00e676 !important; color: #00e676 !important; }</style>""", unsafe_allow_html=True)
        menu_map = {"공지사항": 1, "명부": 2, "참여율": 3, "로그": 4}
        active_idx = menu_map.get(st.session_state.current_menu, 1)
        st.markdown(f"""<style>[data-testid="stSidebarUserContent"] div.stButton:nth-child({active_idx + 2}) > button {{ border-color: #00e676 !important; color: #00e676 !important; background-color: rgba(0, 230, 118, 0.12) !important; }}</style>""", unsafe_allow_html=True)
    else:
        menu_map = {"공지사항": 1, "명부": 2, "참여율": 3, "로그": 4}
        active_idx = menu_map.get(st.session_state.current_menu, 1)
        st.markdown(f"""<style>[data-testid="stSidebarUserContent"] div.stButton:nth-child({active_idx + 2}) > button {{ border-color: #00e676 !important; color: #00e676 !important; background-color: rgba(0, 230, 118, 0.12) !important; box-shadow: 0 0 10px rgba(0, 230, 118, 0.2) !important; }}</style>""", unsafe_allow_html=True)


# ==========================================
# 🚨 5. 전용 패스워드 독립 페이지 모드
# ==========================================
if st.session_state.auth_target is not None:
    target_name = "👑 간부 관리자 권한" if st.session_state.auth_target == "admin" else "⚙️ 관제 센터 마스터 설정"
    
    st.markdown(f"""
    <div class="auth-box">
        <h2 style="color: #00e676; margin-bottom: 5px;">🔒 보안 인증</h2>
        <p style="color: #888888; font-size: 0.95rem;">{target_name} 진입을 위한 비밀번호를 기입하세요.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("isolated_password_form", clear_on_submit=True):
        input_pwd = st.text_input("PASSWORD INPUT", type="password", label_visibility="collapsed", placeholder="비밀번호를 입력하세요...")
        c_sub, c_esc = st.columns(2)
        
        btn_login = c_sub.form_submit_button("🔓 인증 및 로그인", use_container_width=True)
        btn_cancel = c_esc.form_submit_button("↩️ 돌아가기", use_container_width=True)
        
        if btn_login:
            if input_pwd == st.session_state.admin_password:
                if st.session_state.auth_target == "admin":
                    st.session_state.is_admin = True
                    st.session_state.auth_target = None
                elif st.session_state.auth_target == "config":
                    st.session_state.is_admin = True 
                    st.session_state.current_menu = "환경설정"
                    st.session_state.auth_target = None
                st.rerun()
            else:
                st.error("❌ 비밀번호가 다릅니다. 다시 확인해 주세요.")
                
        if btn_cancel:
            st.session_state.auth_target = None
            st.rerun()

else:
    # ----------------------------------------
    # 본문 기본 대시보드 인터페이스 마스터 프레임
    # ----------------------------------------
    if st.session_state.is_admin:
        st.markdown('<div style="text-align: right; color: #00e676; font-size: 0.85rem; font-weight: bold; padding-right: 10px;">🛡️ 간부 관리 모드 가동 중</div>', unsafe_allow_html=True)

    st.markdown(f'<div style="color: #00e676; font-size: 2.3rem; font-weight: bold; margin-bottom: 2px;">{st.session_state.current_menu}</div>', unsafe_allow_html=True)
    st.caption(f"다내꺼 관제 대시보드 > {st.session_state.current_menu}")
    st.markdown("<hr style='border-color:#2d2d2d;'>", unsafe_allow_html=True)

    # ==========================================
    # ⚙️ [분리된 메뉴] 환경설정 구역
    # ==========================================
    if st.session_state.current_menu == "환경설정":
        st.subheader("⚙️ 마스터 시스템 환경설정")
        st.info("디스코드, 카카오톡 주소 및 진입 패스워드를 통합 제어하는 전용 제어반입니다.")
        
        with st.form("dashboard_config_form"):
            st.markdown("#### 1. 커뮤니티 다이렉트 연동 링크 수정")
            new_discord = st.text_input("🎮 디스코드 접속 링크", value=st.session_state.discord_url)
            new_kakao = st.text_input("💬 카카오톡 단톡방 링크", value=st.session_state.kakao_url)
            
            st.markdown("---")
            st.markdown("#### 2. 통합 관제 게이트웨이 보안 암호 수정")
            new_password = st.text_input("🔒 신규 마스터 비밀번호 설정", value=st.session_state.admin_password, type="password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            save_config = st.form_submit_button("💾 설정 변경 사항 일괄 저장")
            
            if save_config:
                st.session_state.discord_url = new_discord
                st.session_state.kakao_url = new_kakao
                st.session_state.admin_password = new_password
                st.success("🔥 환경설정이 완벽하게 변경 및 저장되었습니다!")
                st.rerun()
                
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↩️ 일반 모드로 안전 복귀"):
            st.session_state.is_admin = False
            st.session_state.current_menu = "공지사항"
            st.rerun()

    # ==========================================
    # 📌 [콘텐츠 1] 공지사항 구역
    # ==========================================
    elif st.session_state.current_menu == "공지사항":
        if st.session_state.is_admin:
            with st.expander("📝 [간부 전용] 새 공지사항 강제 등록", expanded=True):
                with st.form("new_notice_form", clear_on_submit=True):
                    c_type, _ = st.columns([1, 1])
                    notice_type = c_type.selectbox("공지 유형", ["🚫 통제", "📢 일반", "🔥 긴급", "⚔️ 레이드"])
                    notice_content = st.text_area("공지 내용 내용", placeholder="공지할 내용을 상세히 입력하세요.")
                    
                    submit_notice = st.form_submit_button("💾 공지 등록")
                    if submit_notice:
                        if notice_content.strip() != "":
                            new_id = len(st.session_state.notices) + 1
                            now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                            st.session_state.notices.insert(0, {
                                "id": new_id, "유형": notice_type, "내용": notice_content, "날짜": now_str
                            })
                            st.success("✅ 새로운 공지사항이 하단 전광판에 즉시 업데이트 되었습니다!")
                            st.rerun()
                        else:
                            st.error("내용을 정확히 입력해주세요.")
            st.markdown("<br>", unsafe_allow_html=True)

        for notice in st.session_state.notices:
            st.markdown(f"""
            <div class="notice-card">
                <span class="badge">{notice['유형']}</span> <small style="color:#777">⏰ {notice['날짜']}</small>
                <p style="margin-top:10px; font-size: 1.05rem; line-height: 1.6;">{notice['내용']}</p>
            </div>
            """, unsafe_allow_html=True)

    # ==========================================
    # 👥 [콘텐츠 2] 길드원 명부 구역
    # ==========================================
    elif st.session_state.current_menu == "명부":
        st.subheader("👥 길드 명부 및 전투력 순위")
        
        if st.session_state.is_admin:
            with st.expander("🛠️ 표 상단 타이틀 명칭 수정", expanded=False):
                c1, c2, c3, c4, c5 = st.columns(5)
                st.session_state.headers["col1"] = c1.text_input("1번 칸", value=st.session_state.headers["col1"])
                st.session_state.headers["col2"] = c2.text_input("2번 칸", value=st.session_state.headers["col2"])
                st.session_state.headers["col3"] = c3.text_input("3번 칸", value=st.session_state.headers["col3"])
                st.session_state.headers["col4"] = c4.text_input("4번 칸", value=st.session_state.headers["col4"])
                st.session_state.headers["col5"] = c5.text_input("5번 칸", value=st.session_state.headers["col5"])

        sorted_members = st.session_state.guild_members.sort_values(by="전투력", ascending=False)
        cfg = {
            "캐릭터명": st.column_config.TextColumn(st.session_state.headers["col1"], required=True),
            "클래스": st.column_config.SelectboxColumn(st.session_state.headers["col2"], options=["버서커", "디바인어벤저", "엘리멘탈리스트", "레인저", "뱅가드", "다크프리스트"]),
            "레벨": st.column_config.NumberColumn(st.session_state.headers["col3"], min_value=1, format="%d"),
            "전투력": st.column_config.NumberColumn(st.session_state.headers["col4"], min_value=0, format="%d"),
            "비고": st.column_config.TextColumn(st.session_state.headers["col5"])
        }

        if st.session_state.is_admin:
            edited_df = st.data_editor(sorted_members, use_container_width=True, hide_index=True, num_rows="dynamic", key="member_editor", column_config=cfg)
            if not edited_df.equals(st.session_state.guild_members):
                st.session_state.guild_members = edited_df
                st.rerun()
        else:
            st.dataframe(sorted_members, use_container_width=True, hide_index=True, column_config=cfg)

    # ==========================================
    # 📊 [콘텐츠 3] 보스 참여율 정산 구역
    # ==========================================
    elif st.session_state.current_menu == "참여율":
        if st.session_state.is_admin:
            st.markdown("### 🛠️ 레이드 출석 체크 입력 패널")
            
            c_date, c_boss = st.columns(2)
            raid_date = c_date.date_input("레이드 진행 날짜", datetime.now()).strftime('%Y-%m-%d')
            boss_name = c_boss.selectbox("보스 몬스터 선택", st.session_state.boss_list)
            
            input_method = st.radio("입력 방식을 선택하세요", ["📸 AI 스크린샷 인식 기입", "✍️ 마우스 수동 체크 기입"], horizontal=True)
            all_characters = st.session_state.guild_members["캐릭터명"].tolist()
            
            for char in all_characters:
                if char not in st.session_state.boss_attendance:
                    st.session_state.boss_attendance[char] = 0

            final_selected_chars = []

            if input_method == "📸 AI 스크린샷 인식 기입":
                reader = load_ocr_reader()
                uploaded_file = st.file_uploader("스크린샷 업로드", type=["png", "jpg", "jpeg"])
                if uploaded_file is not None:
                    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                    image = cv2.imdecode(file_bytes, 1)
                    st.image(image, caption="업로드된 스크린샷", channels="BGR", width=400)
                    
                    if st.button("🔍 AI 분석 시작"):
                        with st.spinner("분석 중..."):
                            ocr_results = reader.readtext(image)
                            extracted_text = [res[1].strip() for res in ocr_results]
                            detected_members = [m for m in all_characters if any(m in t for t in extracted_text)]
                            st.session_state.detected_cache = detected_members
                            st.session_state.ocr_done = True
                
                if st.session_state.get("ocr_done", False):
                    found_list = st.session_state.get("detected_cache", [])
                    missing_list = [m for m in all_characters if m not in found_list]
                    cf, cm = st.columns(2)
                    cf.success(f"✅ 인식 ({len(found_list)}명): " + ", ".join(found_list))
                    cm.warning(f"⚠️ 미인식 ({len(missing_list)}명): " + ", ".join(missing_list))
                    final_selected_chars = found_list
            else:
                cols = st.columns(4)
                for idx, char in enumerate(all_characters):
                    with cols[idx % 4]:
                        if st.checkbox(char, key=f"manual_{char}"):
                            final_selected_chars.append(char)

            if st.button("💾 위에 선택된 인원 기입 및 로그 등록"):
                if final_selected_chars:
                    for char in final_selected_chars:
                        st.session_state.boss_attendance[char] += 1
                    st.session_state.raid_logs.append({"날짜": raid_date, "보스명": boss_name, "참여명단": final_selected_chars})
                    st.success("🔥 정산 로그 등록이 완료되었습니다!")
                    if "ocr_done" in st.session_state: st.session_state.ocr_done = False
                    st.rerun()
            st.markdown("---")
            
        st.markdown("### 📊 연합 보스 레이드 누적 참여 순위")
        all_characters = st.session_state.guild_members["캐릭터명"].tolist()
        stat_rows = [{"캐릭터명": char, "누적 참여 횟수": st.session_state.boss_attendance.get(char, 0)} for char in all_characters]
        df_stat = pd.DataFrame(stat_rows).sort_values(by="누적 참여 횟수", ascending=False)
        
        c_tot, c_top = st.columns(2)
        with c_tot:
            st.markdown(f'<div class="stat-card"><span style="color: #888;">👑 최고 참여 명예의 전당</span><div class="stat-number">{df_stat.iloc[0]["캐릭터명"] if not df_stat.empty else "-"}</div></div>', unsafe_allow_html=True)
        with c_top:
            st.markdown(f'<div class="stat-card"><span style="color: #888;">🔥 최고 레이드 참여 기록</span><div class="stat-number">{df_stat.iloc[0]["누적 참여 횟수"] if not df_stat.empty else 0} 회</div></div>', unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df_stat, use_container_width=True, hide_index=True, column_config={"누적 참여 횟수": st.column_config.ProgressColumn("🏅 누적 참여율 (포인트)", min_value=0, max_value=100, format="%d 회")})

    # ==========================================
    # 📜 [콘텐츠 4] 레이드 기록 로그 타임라인 구역
    # ==========================================
    elif st.session_state.current_menu == "로그":
        st.subheader("📜 레이드 정산 히스토리 로그")
        
        if st.session_state.raid_logs:
            summary_rows = [{"인덱스": idx, "📅 레이드 일자": log["날짜"], "⚔️ 정산 보스": log["보스명"], "👥 총 참여 인원수": f"{len(log['참여명단'])} 명"} for idx, log in enumerate(st.session_state.raid_logs)]
            df_summary = pd.DataFrame(summary_rows).sort_values(by="📅 레이드 일자", ascending=False)
            
            st.dataframe(df_summary, use_container_width=True, hide_index=True, column_config={"인덱스": None})
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🔍 개별 레이드 명단 상세보기")
            
            log_options = [f"[{log['날짜']}] {log['보스명']} (총 {len(log['참여명단'])}명)" for log in st.session_state.raid_logs]
            selected_log_title = st.selectbox("참여 명단을 조회할 레이드를 선택하세요", log_options)
            
            selected_idx = log_options.index(selected_log_title)
            target_log = st.session_state.raid_logs[selected_idx]
            
            st.markdown(f"**🎯 `{target_log['보스명']}` 참여 명단 현황**")
            member_cols = st.columns(5)
            for m_idx, m_name in enumerate(target_log["참여명단"]):
                with member_cols[m_idx % 5]:
                    st.markdown(f"• `{m_name}`")
