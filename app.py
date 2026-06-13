# ==========================================
# 명부
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

        # ✅ 신규 멤버 추가 폼
        with st.expander("➕ 새 길드원 추가", expanded=False):
            with st.form("add_member_form", clear_on_submit=True):
                a1, a2, a3, a4, a5 = st.columns(5)
                new_name  = a1.text_input(st.session_state.headers["col1"])
                new_class = a2.selectbox(st.session_state.headers["col2"], ["버서커", "디바인어벤저", "엘리멘탈리스트", "레인저", "뱅가드", "다크프리스트"])
                new_level = a3.number_input(st.session_state.headers["col3"], min_value=1, value=1, step=1)
                new_power = a4.number_input(st.session_state.headers["col4"], min_value=0, value=0, step=100)
                new_note  = a5.text_input(st.session_state.headers["col5"])
                if st.form_submit_button("➕ 추가", use_container_width=True):
                    if new_name.strip():
                        new_row = pd.DataFrame([{"캐릭터명": new_name, "클래스": new_class, "레벨": int(new_level), "전투력": int(new_power), "비고": new_note}])
                        st.session_state.guild_members = pd.concat([st.session_state.guild_members, new_row], ignore_index=True)
                        save_members(st.session_state.guild_members)
                        st.toast("✅ 새 길드원이 추가되었습니다.")
                        st.rerun()
                    else:
                        st.error("캐릭터명을 입력해주세요.")

    sorted_members = st.session_state.guild_members.sort_values(by="전투력", ascending=False).reset_index(drop=True)

    # 헤더 행
    h1, h2, h3, h4, h5, h6 = st.columns([2.5, 2, 1, 1.5, 1.5, 1])
    for col, label in zip([h1, h2, h3, h4, h5], [
        st.session_state.headers["col1"], st.session_state.headers["col2"],
        st.session_state.headers["col3"], st.session_state.headers["col4"],
        st.session_state.headers["col5"]
    ]):
        col.markdown(f"<div style='color:#00e676; font-weight:bold; font-size:0.85rem; padding:4px 0;'>{label}</div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#2d2d2d; margin:4px 0 8px 0;'>", unsafe_allow_html=True)

    class_options = ["버서커", "디바인어벤저", "엘리멘탈리스트", "레인저", "뱅가드", "다크프리스트"]

    for i, row in sorted_members.iterrows():
        if st.session_state.is_admin:
            # ✅ 관리자: 각 행을 폼으로 인라인 편집
            with st.form(f"edit_row_{i}"):
                c1, c2, c3, c4, c5, c6 = st.columns([2.5, 2, 1, 1.5, 1.5, 1])
                e_name  = c1.text_input("이름",  value=str(row["캐릭터명"]), label_visibility="collapsed", key=f"n_{i}")
                e_class = c2.selectbox("클래스", class_options, index=class_options.index(row["클래스"]) if row["클래스"] in class_options else 0, label_visibility="collapsed", key=f"c_{i}")
                e_level = c3.number_input("레벨", value=int(row["레벨"]), min_value=1, step=1, label_visibility="collapsed", key=f"l_{i}")
                e_power = c4.number_input("전투력", value=int(row["전투력"]), min_value=0, step=100, label_visibility="collapsed", key=f"p_{i}")
                e_note  = c5.text_input("비고",  value=str(row["비고"]), label_visibility="collapsed", key=f"note_{i}")
                col_save, col_del = c6.columns(2)
                btn_save = col_save.form_submit_button("💾")
                btn_del  = col_del.form_submit_button("🗑️")

                if btn_save:
                    st.session_state.guild_members.loc[
                        st.session_state.guild_members["캐릭터명"] == row["캐릭터명"], :
                    ] = [e_name, e_class, int(e_level), int(e_power), e_note]
                    save_members(st.session_state.guild_members)
                    st.toast(f"✅ {e_name} 저장 완료")
                    st.rerun()

                if btn_del:
                    st.session_state.guild_members = st.session_state.guild_members[
                        st.session_state.guild_members["캐릭터명"] != row["캐릭터명"]
                    ].reset_index(drop=True)
                    save_members(st.session_state.guild_members)
                    st.toast(f"🗑️ {row['캐릭터명']} 삭제 완료")
                    st.rerun()
        else:
            # 일반 유저: 읽기 전용 행
            c1, c2, c3, c4, c5, c6 = st.columns([2.5, 2, 1, 1.5, 1.5, 1])
            c1.markdown(f"<div style='padding:10px 0; font-size:0.95rem;'>{row['캐릭터명']}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div style='padding:10px 0; color:#aaa;'>{row['클래스']}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='padding:10px 0; color:#aaa;'>{int(row['레벨'])}</div>", unsafe_allow_html=True)
            c4.markdown(f"<div style='padding:10px 0; color:#00e676; font-weight:bold;'>{int(row['전투력']):,}</div>", unsafe_allow_html=True)
            c5.markdown(f"<div style='padding:10px 0; color:#aaa;'>{row['비고']}</div>", unsafe_allow_html=True)
            st.markdown("<div style='border-bottom:1px solid #2d2d2d; margin:2px 0;'></div>", unsafe_allow_html=True)
