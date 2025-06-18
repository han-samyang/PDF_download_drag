import streamlit as st
import pandas as pd
import requests
import zipfile
import io
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- 설정 영역 ---
POSSIBLE_COLUMN_NAMES = ["원문(PDF)링크", "출원번호"]

# --- UI 설정 ---
st.set_page_config(page_title="윕스온 PDF 다운로더", page_icon="📑")
st.markdown(
    """
    <div style="display: flex; align-items: center;">
        <img src="https://www.wips-on.com/images/common/logo_header_on.png" width="80">
        <h1 style="margin-left: 20px; color: #2d7dd2;">📑 윕스온 PDF 링크 다운로더</h1>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

# --- 사용법 안내 (강조 박스) ---
with st.expander("💡 사용법 보기", expanded=False):
    st.markdown("""
    <div style="background-color: #e6f2ff; border-radius: 8px; padding: 15px;">
    <b>이 앱은 윕스온(WIPS On) 특허 페이지 링크가 담긴 엑셀 파일을 업로드하면,<br>
    각 페이지에서 숨겨진 PDF 파일을 자동으로 찾아 ZIP 파일로 만들어줍니다.</b>
    <ul>
        <li>📁 <b>엑셀 파일 준비</b>: <span style="color:#2d7dd2;">'원문(PDF)링크'</span> 또는 <span style="color:#2d7dd2;">'출원번호'</span> 열이 포함된 엑셀 파일을 준비하세요.</li>
        <li>⚡ <b>파일 업로드</b>: 아래 <span style="color:#2d7dd2;">'엑셀 파일 업로드'</span> 버튼을 클릭하세요.</li>
        <li>🗂️ <b>다운로드</b>: 작업 완료 후 ZIP 파일 받기!</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

# --- 파일 업로더 ---
uploaded_file = st.file_uploader("📁 엑셀 파일 업로드", type=['xlsx', 'xls'], help="엑셀 파일에는 '원문(PDF)링크' 또는 '출원번호' 열이 포함되어야 합니다.")

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        found_column_name = None
        for name in POSSIBLE_COLUMN_NAMES:
            if name in df.columns:
                found_column_name = name
                break

        if found_column_name is None:
            st.error("🚫 필수 열이 없습니다! 엑셀 파일에 '원문(PDF)링크' 또는 '출원번호' 열이 포함되어야 합니다.")
            st.warning(f"현재 파일 열: {', '.join(df.columns)}")
            st.stop()
        
        st.success(f"🎉 [{found_column_name}] 열을 기준으로 작업을 시작합니다!")
        with st.expander("🔍 업로드한 데이터 미리보기", expanded=False):
            st.dataframe(df)

        if st.button("⚡ PDF 추출 및 다운로드 시작"):
            page_links = df[found_column_name].dropna().astype(str).tolist()
            page_links = [link for link in page_links if link.strip().startswith('http')]

            if not page_links:
                st.warning("🔔 유효한 링크가 없습니다. (http로 시작하는지 확인)")
                st.stop()
            
            st.info(f"💡 {len(page_links)}개의 웹페이지에서 PDF 링크를 추출합니다...")

            progress_bar = st.progress(0, text="🕓 대기 중...")
            zip_buffer = io.BytesIO()
            success_count = 0
            error_links = []
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for i, page_link in enumerate(page_links):
                    progress_text = f"({i+1}/{len(page_links)}) 🔗 페이지 분석 중..."
                    progress_bar.progress((i + 1) / len(page_links), text=progress_text)
                    try:
                        response = requests.get(page_link, headers=headers, timeout=15)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.text, 'lxml')
                        iframe = soup.find('iframe', id='ifrm')
                        
                        if iframe and iframe.has_attr('src'):
                            pdf_link = urljoin(page_link, iframe['src'])
                            pdf_response = requests.get(pdf_link, headers=headers, timeout=30)
                            pdf_response.raise_for_status()

                            file_name = pdf_link.split('/')[-1].split('#')[0].split('?')[0]
                            if not file_name or not file_name.lower().endswith(".pdf"):
                                file_name = f"document_{i+1}.pdf"
                            
                            zip_file.writestr(file_name, pdf_response.content)
                            success_count += 1
                        else:
                            error_links.append((page_link, "페이지에서 PDF 링크(iframe)를 찾지 못함"))
                    except Exception as e:
                        error_links.append((page_link, str(e)))

            progress_bar.progress(1.0, text="✨ 모든 작업 완료!")
            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("🎉 성공 건수", f"{success_count} 건")
            with col2:
                st.metric("⚠️ 실패 건수", f"{len(error_links)} 건")
            
            if success_count > 0:
                st.balloons()
                st.success("🗂️ PDF 다운로드가 완료되었습니다! 아래 버튼을 눌러 ZIP 파일을 저장하세요.")
                zip_buffer.seek(0)
                st.download_button(
                    label=f"🗂️ {success_count}개 PDF ZIP 다운로드",
                    data=zip_buffer,
                    file_name="wipson_pdfs.zip",
                    mime="application/zip",
                    use_container_width=True
                )
            else:
                st.error("🚫 다운로드한 PDF 파일이 없습니다.")
                
            if error_links:
                with st.expander("🔔 실패한 링크 및 오류 원인 보기", expanded=False):
                    st.dataframe(pd.DataFrame(error_links, columns=['링크 주소', '오류 원인']))

    except Exception as e:
        st.error(f"❗ 치명적 오류 발생: {e}")

