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
    height=150
)

days = st.slider("生成日数", 1, 60, 30)
tweets_per_day = st.slider("1日あたりのツイート数", 1, 5, 2)  # 新規：1日2ツイート対応

st.subheader("エロ度調整")
erotic_level = st.slider("エロ度（1: 控えめ → 10: 生々しい）", min_value=1, max_value=10, value=5)

st.subheader("ツイート長調整")
tweet_length = st.slider("ツイート長（1: 短め → 10: 長め）", min_value=1, max_value=10, value=6)

st.subheader("生成ルール")
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
emoji_ban = col1.checkbox("絵文字禁止", value=False)
hashtag_ban = col2.checkbox("ハッシュタグ禁止", value=False)
newline_allow = col3.checkbox("改行を適切に使用", value=True)
newline_ban = col4.checkbox("改行完全禁止", value=False)
dm_invite = col5.checkbox("連絡誘導を入れる", value=False)
sensitive_avoid = col6.checkbox("センシティブ回避（暗示表現）", value=True)
fuzzy_mode = col7.checkbox("伏字モード", value=False)

custom_rule = st.text_input("その他ルール")

if st.button("生成開始"):
    if not features or not API_KEY:
        st.error("特徴とAPIキーを入力してください")
    else:
        rule_text = ""
        if emoji_ban: rule_text += "絵文字は一切使用禁止。"
        if hashtag_ban: rule_text += "ハッシュタグは一切使用禁止。"
        if newline_ban: rule_text += "改行は一切使用禁止。"
        if newline_allow: rule_text += "自然で読みやすい位置に適度な改行を挿入（2-4行程度）。"
        if dm_invite: rule_text += "ツイート末尾に自然な連絡誘導文を入れる（例: 「気になったら声かけてね」「リプください」「連絡待ってる」など。「DM」という単語は絶対に使わない）。"
        if sensitive_avoid: rule_text += "Xのセンシティブ判定を回避するため、直接的な性器名・行為名は一切使わず、暗示的・比喩・感覚的な表現のみで描写（例: 「濡れる」→「熱が溢れる」「とろけそう」）。"
        if fuzzy_mode: rule_text += "センシティブな言葉は伏字化（例: ま◯こ、ち◯ぽ、おっぱ◯）またはマイルド表現に置き換え。"
        rule_text += custom_rule

        # エロ度指示
        if erotic_level <= 3:
            erotic_instruction = "エロティックさは控えめで、直接的な表現を避け、雰囲気や暗示で表現。"
        elif erotic_level <= 7:
            erotic_instruction = "中程度のエロティック表現を使用。感覚的な描写を適度に取り入れる。"
        else:
            erotic_instruction = "生々しく大胆なエロティック表現を積極的に使用。具体的な描写も可。"

        # ツイート長指示
        if tweet_length <= 3:
            length_instruction = "ツイートは短め（100文字以内）で簡潔に。"
        elif tweet_length <= 7:
            length_instruction = "ツイートは中程度の長さ（150〜200文字程度）。"
        else:
            length_instruction = "ツイートは長め（220〜280文字）で詳細に描写。"

        # 重複禁止指示
        repeat_prevention = "すべてのツイートで表現・シチュエーション・言い回しを多様化し、同じような内容やフレーズの繰り返しを厳禁とする。"

        reference_prompt = f"参考スタイル: {reference}" if reference else ""

        with st.spinner(f"{days}日分（{days * tweets_per_day}ツイート）生成中..."):
            today = datetime.date.today()
            dates = [today - datetime.timedelta(days=i) for i in range(days)]  # 今日から遡る（今日含む）
            dates.reverse()  # 最新日（今日）から古い順
            date_strings = []
            tweets = []

            for date in dates:
                date_str = date.strftime("%Y-%m-%d")
                for j in range(tweets_per_day):  # 1日あたりのツイート数分ループ
                    time_label = f"投稿{j+1}"  # 例: 投稿1, 投稿2
                    prompt = f"""
                    厳格に以下の指示で裏垢女子のツイートを1つ生成。
                    - 特徴: {features}
                    {reference_prompt}
                    - 日付考慮: {date_str}頃（{time_label}）
                    - ルール: {rule_text}
                    - エロ度: {erotic_instruction}
                    - 長さ: {length_instruction}
                    - 重複禁止: {repeat_prevention}
                    - 280文字以内、フィクション、秘密めいた内容
                    - 出力: ツイート本文のみ
                    """
                    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
                    data = {
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.95,
                        "max_tokens": 350
                    }
                    response = requests.post(API_URL, headers=headers, json=data)
                    if response.status_code == 200:
                        tweet = response.json()["choices"][0]["message"]["content"].strip()
                    else:
                        tweet = f"エラー: {response.text[:100]}"
                    tweets.append(tweet)
                    date_strings.append(f"{date_str} ({time_label})")

            df = pd.DataFrame({"Date": date_strings, "Tweet": tweets})
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("CSVダウンロード", csv, "tweets.csv", "text/csv")
            st.dataframe(df)

st.info("生成時のみクレジット消費。初回は数円程度です。")
