import streamlit as st
import datetime
import pandas as pd
import requests
import io
import re
import base64
import os
from PIL import Image

# --- 設定：保存先 ---
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

SAVE_FILE = os.path.join(DATA_DIR, "current_state.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "feature_history.csv")

st.set_page_config(page_title="裏垢女子プロンプト生成 v1.09", layout="wide")

# --- データの読み込み・保存 ---
def save_data(features, history):
    pd.DataFrame({"features": [features]}).to_csv(SAVE_FILE, index=False)
    unique_history = list(dict.fromkeys(history))
    pd.DataFrame({"history": unique_history[-100:]}).to_csv(HISTORY_FILE, index=False)

def load_data():
    features, history = "", []
    if os.path.exists(SAVE_FILE):
        try: features = pd.read_csv(SAVE_FILE)["features"][0]
        except: pass
    if os.path.exists(HISTORY_FILE):
        try: history = pd.read_csv(HISTORY_FILE)["history"].tolist()
        except: pass
    return features, history

init_features, init_history = load_data()
if "current_features" not in st.session_state:
    st.session_state.current_features = init_features
if "feature_history" not in st.session_state:
    st.session_state.feature_history = init_history

# API設定
if "GROK_API_KEY" in st.secrets:
    API_KEY = st.secrets["GROK_API_KEY"]
else:
    API_KEY = st.sidebar.text_input("Grok APIキーを入力", type="password")
API_URL = "https://api.x.ai/v1/chat/completions"

# --- メインUI ---
st.title("裏垢女子プロンプト生成 v3.5")
st.caption("AIが毎回新しいシチュエーションを考案します。リロードしてもデータは保持されます。")

selected_model = st.sidebar.selectbox("AI Model", ["grok-vision-beta", "grok-4-1-fast-reasoning"])

col_input, col_preview = st.columns([2, 1])

with col_input:
    st.subheader("🛠️ 設定構築")
    
    # 1. AIランダマイザー（ここが進化ポイント）
    if st.button("🎲 AIにシチュエーションを丸投げする"):
        if not API_KEY:
            st.error("APIキーを入力してください")
        else:
            with st.spinner("AIがエロティックなシチュエーションを考案中..."):
                rand_prompt = "裏垢女子の画像生成用の設定を作りたいです。『場所』と『服装』の組み合わせを、背徳感のある絶妙な設定で1つだけ提案してください。出力は「場所：〇〇、服装：××」という形式で1行だけでお願いします。余計な解説は不要です。"
                try:
                    r = requests.post(
                        API_URL,
                        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                        json={"model": "grok-4-1-fast-reasoning", "messages": [{"role": "user", "content": rand_prompt}]}
                    )
                    ai_suggestion = r.json()["choices"][0]["message"]["content"].strip()
                    # 現在の特徴に追記
                    st.session_state.current_features += f"\n【AI提案: {ai_suggestion}】"
                    save_data(st.session_state.current_features, st.session_state.feature_history)
                    st.rerun()
                except:
                    st.error("AI提案の取得に失敗しました")

    # 特徴入力
    features = st.text_area(
        "女性の特徴・現在の設定", 
        value=st.session_state.current_features,
        height=180,
        key="main_features"
    )
    if features != st.session_state.current_features:
        st.session_state.current_features = features
        save_data(features, st.session_state.feature_history)

    # 履歴復元
    if st.session_state.feature_history:
        selected_h = st.selectbox("過去の履歴から復元", ["-- 選択 --"] + st.session_state.feature_history[::-1])
        if selected_h != "-- 選択 --" and st.button("復元実行"):
            st.session_state.current_features = selected_h
            save_data(selected_h, st.session_state.feature_history)
            st.rerun()

with col_preview:
    st.subheader("📸 参考画像")
    uploaded_file = st.file_uploader("画像をUP（忠実に再現）", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, use_container_width=True)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

# --- 最終的なプロンプト生成 ---
st.divider()
if st.button("✨ 最終的な英語プロンプトを生成", type="primary"):
    if not st.session_state.current_features and not uploaded_file:
        st.error("設定を入力してください")
    elif not API_KEY:
        st.error("APIキーがありません")
    else:
        # 新しい特徴なら履歴に登録
        if st.session_state.current_features not in st.session_state.feature_history:
            st.session_state.feature_history.append(st.session_state.current_features)
            save_data(st.session_state.current_features, st.session_state.feature_history)

        with st.spinner("プロンプト作成中..."):
            prompt_content = [
                {"type": "text", "text": f"以下の設定に基づき、リアリティのある裏垢女子の画像生成用英語プロンプト（Midjourney/Stable Diffusion形式）を作成してください。画像がある場合はその女性の特徴を優先して。設定：{st.session_state.current_features}"}
            ]
            if uploaded_file:
                prompt_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}})

            response = requests.post(
                API_URL, 
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={"model": selected_model, "messages": [{"role": "user", "content": prompt_content}]}
            )
            st.markdown(response.json()["choices"][0]["message"]["content"])
