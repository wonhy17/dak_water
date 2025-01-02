from openai import OpenAI
import streamlit as st
import time
import os
from dotenv import load_dotenv
from PIL import Image
import requests
import io
import base64
import smtplib
import datetime
from pyairtable import Table, Base
import streamlit.components.v1 as components

# Airtable API 정보
TABLE_NAME = "Threads"

def get_message():
    time.sleep(3)  # 3초간 지연 (예: API 요청 대기)

#시간 조작
now = datetime.datetime.now()
formatted_time = now.strftime("%y/%m/%d %I:%M %p")

#창이 열린 시점의 시간 기록
window_open_time = time.time()

# 1) .env 파일 로드
load_dotenv()

# 2) 환경 변수에서 값 가져오기
openai_api_key = os.getenv("OPENAI_API_KEY")
airtable_api_key = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("BASE_ID")
TABLE_NAME = os.getenv("TABLE_NAME")

client = OpenAI(api_key=openai_api_key)

assistant_id = os.getenv("ASSISTANT_ID")

if "thread_id" not in st.session_state:
    thread = client.beta.threads.create(
        
    )
    thread_id = thread.id
    st.session_state["thread_id"] = thread_id

print(st.session_state)

# code to hide the watermark using CSS
components.html("""
    <style>
    footer {visibility: hidden;}
    </style>
""", height=0)
# #MainMenu to hide the burger menu at the top-right side
# footer to hide the ```made with streamlit``` mark
hide = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        footer:after {content: ''; display: block; position: absolute; bottom: 0; left: 0; height: 0; width: 100%; background: transparent;}
    </style>
"""
st.markdown(hide, unsafe_allow_html=True)

st.components.v1.html("""
<script>
    if (/Mobi|Android/i.test(navigator.userAgent)) {
        alert("모바일 환경에서는 뒤로가기를 누르면 앱이 종료될 수 있습니다. 닫기 버튼을 사용하세요!");
    }
</script>
""")

# 이미지 표시 섹션 (사이드바)
with st.sidebar:
    # 추가로 로컬 이미지나 URL 이미지를 표시할 수 있음
    # 로컬 이미지 경로 리스트
    image_paths = [
        os.path.join("file", "원홀과 투홀 차이.png"),
        os.path.join("file", "원홀 수전 리스트.jpg"),
        os.path.join("file", "투홀 수전 리스트.jpg"),
        os.path.join("file", "싱크대 수전 리스트.jpg"),
        os.path.join("file", "샤워기 수전 리스트.jpg"),
    ]
    st.subheader("이미지 보기")
    for image_path in image_paths:
        image = Image.open(image_path)
        st.image(image, caption=image_path, use_container_width=True)
    
st.markdown("<h1 style='font-size: 30px;'>뚝닥 수전 전용 챗봇 🚿</h1>", unsafe_allow_html=True)
if "messages" not in st.session_state:
    #st.image(image_path, caption=caption, use_column_width=True)
    st.session_state["messages"] = [{"role": "assistant", "content": "반갑습니다! \n\n 상황을 1줄 이내로 말씀해주시면 6~7가지 필수 사전 질문 답변 후 최종 예약 및 견적 확인을 진행할 수 있습니다. \n\n 기타 문제 발생 시시, 1551-7784로 문의주세요!"}]
    
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])
    
if prompt := st.chat_input():
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()
    
    client = OpenAI(api_key=openai_api_key)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    response = client.beta.threads.messages.create(
        thread_id=st.session_state["thread_id"],
        role="user",
        content=prompt
    )
        
    run = client.beta.threads.runs.create(
        thread_id=st.session_state["thread_id"],
        assistant_id = assistant_id
    )
        
    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state["thread_id"],
            run_id = run.id
        )
        # 스피너를 이용하여 로딩 애니메이션 표시
        with st.spinner('Getting your message...'):
            message = get_message()
            
        if run.status == 'completed':
            break
        else:
            time.sleep(0.5)
    
    thread_messages = client.beta.threads.messages.list(st.session_state["thread_id"])
    
    msg = thread_messages.data[0].content[0].text.value

    table = Table(airtable_api_key, BASE_ID, TABLE_NAME)

    table.create({
        'thread_id': st.session_state["thread_id"][-4:],
        '시간': formatted_time,
        '고객': response.content[0].text.value,
        'AI': msg,
        }
    )
    
    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant").write(msg)