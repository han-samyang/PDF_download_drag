import streamlit as st
import requests
import zipfile
import io
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- 페이지 설정 ---
st.set_page_config(page_title="PDF 링크 다운로더", page_icon="📋")
st.title("📋 드래그&붙여넣기 PDF 다운로더")

# --- 사용법 안내 ---
with st.expander("💡 사용법 보기", expanded=True):
    st.markdown("""
    <div style="background-color: #e6f2ff; border-radius: 8px; padding: 15px;">
    1. 엑셀/메모장에서 링크 복사 → 아래 박스에 붙여넣기<br>
    2. [PDF 추출 시작] 버튼 클릭<br>
    3. 완료 시 ZIP 파일 다운로드
    </div>
    """, unsafe_allow_html=True)

# --- 링크 입력 영역 ---
link_text = st.text_area(
    "🔗 링크 붙여넣기 (여러 줄 가능)",
    height=200,
    placeholder="예시:\nhttps://example.com/file1\nhttps://example.com/file2"
)

if link_text:
    # 링크 파싱 (탭/쉼표/줄바꿈 모두 처리)
    raw_links = link_text.replace('\t', '\n').replace(',', '\n').splitlines()
    page_links = [link.strip() for link in raw_links if link.strip().startswith('http')]

    st.success(f"✅ {len(page_links)}개의 유효한 링크가 인식되었습니다!")

    if st.button("⚡ PDF 추출 시작", type="primary"):
        progress_bar = st.progress(0, text="🕓 초기화 중...")
        zip_buffer = io.BytesIO()
        success_count = 0
        error_log = []

        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for idx, url in enumerate(page_links, 1):
                try:
                    # 진행상황 업데이트
                    progress = idx/len(page_links)
                    progress_bar.progress(progress, text=f"📥 {idx}/{len(page_links)} 처리 중 - {url[:30]}...")

                    # PDF 링크 추출
                    response = requests.get(url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    iframe = soup.find('iframe', {'id': 'ifrm'})
                    
                    if iframe and iframe.get('src'):
                        pdf_url = urljoin(url, iframe['src'])
                        
                        # PDF 다운로드
                        pdf_response = requests.get(pdf_url, timeout=15)
                        pdf_response.raise_for_status()
                        
                        # 파일명 생성
                        file_name = (
                            pdf_url.split('/')[-1]
                            .split('?')[0]
                            .split('#')[0]
                            .replace(' ', '_')
                        )
                        if not file_name.endswith('.pdf'):
                            file_name += '.pdf'
                        
                        # ZIP에 추가
                        zip_file.writestr(file_name, pdf_response.content)
                        success_count += 1

                    else:
                        error_log.append(f"{url} - iframe 미탐색")

                except Exception as e:
                    error_log.append(f"{url} - {str(e)}")

        # 결과 표시
        progress_bar.empty()
        st.markdown("---")
        st.metric("🎉 성공한 파일 수", success_count)
        
        if success_count > 0:
            st.success("파일 준비 완료! 아래 버튼으로 다운로드 하세요.")
            st.download_button(
                label="🗂️ ZIP 파일 다운로드",
                data=zip_buffer.getvalue(),
                file_name="downloads.zip",
                mime="application/zip"
            )
        
        if error_log:
            with st.expander("⚠️ 실패 목록 보기"):
                st.write("\n".join(error_log))
