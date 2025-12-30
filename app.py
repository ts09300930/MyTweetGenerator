import streamlit as st
import datetime
import pandas as pd
import requests

st.title("裏垢女子ツイート生成ツール")

# APIキー管理
if "GROK_API_KEY" in st.secrets:
    API_KEY = st.secrets["GROK_API_KEY"]
else:
    API_KEY = st.text_input("Grok APIキー（ローカルテスト用）", type="password")

API_URL = "https://api.x.ai/v1/chat/completions"

# モデル選択
model_options = [
    "grok-4-1-fast-reasoning (低コスト・推奨)",
    "grok-4-1-fast-non-reasoning",
    "grok-4-fast-reasoning",
    "grok-4 (高性能・高コスト)"
]
selected_model = st.selectbox("使用モデルを選択", model_options, index=0)
model_name = selected_model.split(" (")[0]

# UI入力
features = st.text_area(
    "裏垢女子の特徴を入力",
    placeholder="例: 20代後半OL、欲求不満、エロティックな日常吐露",
    height=150
)

reference = st.text_area(
    "参考スタイル（オプション）\nXアカウントURLや過去ツイート例を貼り付け",
    placeholder="例: 短文中心、特定の口癖を使う",
    height=150
)

days = st.slider("生成日数", 1, 60, 30)

st.subheader("生成ルール")
col1, col2, col3 = st.columns(3)
emoji_ban = col1.checkbox("絵文字禁止", value=True)
hashtag_ban = col2.checkbox("ハッシュタグ禁止", value=True)
newline_ban = col3.checkbox("改行なし", value=True)
custom_rule = st.text_input("その他ルール")

if st.button("生成開始"):
    if not features or not API_KEY:
        st.error("特徴とAPIキーを入力してください")
    else:
        rule_text = ""
        if emoji_ban: rule_text += "絵文字は一切禁止。"
        if hashtag_ban: rule_text += "ハッシュタグは一切禁止。"
        if newline_ban: rule_text += "改行は一切禁止。"
        rule_text += custom_rule

        reference_prompt = f"参考スタイル: {reference}" if reference else ""

        with st.spinner(f"{days}日分生成中..."):
            today = datetime.date.today()
            dates = [today - datetime.timedelta(days=i) for i in range(days-1, -1, -1)]
            date_strings = [d.strftime("%Y-%m-%d") for d in dates]
            tweets = []

            for date in date_strings:
                prompt = f"""
                以下の指示で裏垢女子のツイートを1つ生成。
                - 特徴: {features}
                {reference_prompt}
                - 日付考慮: {date}頃
                - ルール: {rule_text}
                - 280文字以内、フィクション、エロティックで秘密めいた内容
                - 出力: ツイート本文のみ
                """
                headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
                data = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.9,
                    "max_tokens": 300
                }
                response = requests.post(API_URL, headers=headers, json=data)
                if response.status_code == 200:
                    tweet = response.json()["choices"][0]["message"]["content"].strip()
                else:
                    tweet = f"エラー: {response.text[:100]}"
                tweets.append(tweet)

            df = pd.DataFrame({"Date": date_strings, "Tweet": tweets})
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("CSVダウンロード", csv, "tweets.csv", "text/csv")
            st.dataframe(df)

st.info("生成時のみクレジット消費。初回は数円程度です。")
