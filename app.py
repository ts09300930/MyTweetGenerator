import streamlit as st
import datetime
import pandas as pd
import requests
import io

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

# 参考スタイルをデフォルトで常時入力（分析強化版）
default_reference = """
参考アカウントの書き方・フォーマットを厳守（内容は絶対にパクリせず、特徴に基づくオリジナルで生成）:
全体共通: 改行を多用して読みやすく、寂しさ・欲求・孤独感を強調。自然な連絡誘導（リプください、声かけてねなど）。自己卑下や設定アピールで共感を誘う。短文中心で切実さを出して誘導文を末尾に。
@NextMrsGerrard: 初老限定募集、落ち込み・ショック表現、改行強調、リンク誘導。
@cpc6MkXOxY54448: S気質・便器アピール、直球募集、出したい人呼びかけ。
@sx14e: 家出少女設定、助けを求める切実さ、なんでもします誘導、改行多用。
@siznp82913: 台湾人設定、外国人アピール、迷惑かけない強調、日本大好き表現。
@nico_chan714: 貧乳コンプレックス、自己卑下（小さいけどいいですか？）、質問形式でエンゲージメント。
DM単語避け、誘導は自然に。
"""

# CSV読み込み機能（キャラ選択）
uploaded_csv = st.file_uploader("保存したCSVからキャラ設定を読み込み", type=["csv"])
if uploaded_csv is not None:
    try:
        df_loaded = pd.read_csv(uploaded_csv)
        char_names = ["新規作成"] + df_loaded["Character Name"].dropna().unique().tolist()
        selected_char = st.selectbox("キャラを選択して設定を復元", char_names)
        if selected_char != "新規作成":
            row = df_loaded[df_loaded["Character Name"] == selected_char].iloc[0]
            features = row["Features"]
            reference = row["Reference"]
            days = int(row["Days"])
            tweets_per_day = int(row["Tweets Per Day"])
            erotic_level = int(row["Erotic Level"])
            tweet_length = int(row["Tweet Length"])
            question_frequency = int(row["Question Frequency"])
            self_deprecation_level = int(row["Self Deprecation Level"])
            recruit_type = row["Recruit Type"]
            custom_recruit = row["Custom Recruit"] if pd.notna(row["Custom Recruit"]) else ""
            emoji_ban = bool(row["Emoji Ban"])
            hashtag_ban = bool(row["Hashtag Ban"])
            newline_allow = bool(row["Newline Allow"])
            newline_ban = bool(row["Newline Ban"])
            dm_invite = bool(row["DM Invite"])
            sensitive_avoid = bool(row["Sensitive Avoid"])
            fuzzy_mode = bool(row["Fuzzy Mode"])
            ellipsis_end = bool(row["Ellipsis End"])
            dom_s_mode = bool(row["Dom S Mode"])
            generate_image_prompt = bool(row["Generate Image Prompt"])
            image_prompt_lang = row["Image Prompt Lang"]
            mask_on = bool(row["Mask On"])
            custom_rule = row.get("Custom Rule", "")
            st.success(f"{selected_char}の設定を読み込みました")
    except Exception as e:
        st.error(f"CSV読み込みエラー: {e}")
else:
    selected_char = "新規作成"

# UI入力（読み込み値またはデフォルト）
features = st.text_area("裏垢女子の特徴を入力", value=features if 'features' in locals() else "", placeholder="例: 20代後半OL、欲求不満、エロティックな日常吐露", height=150)
reference = st.text_area("参考スタイル（オプション）\nXアカウントURLや過去ツイート例を貼り付け", value=reference if 'reference' in locals() else default_reference, height=300)
days = st.slider("生成日数", 1, 60, days if 'days' in locals() else 30)
tweets_per_day = st.slider("1日あたりのツイート数", 1, 5, tweets_per_day if 'tweets_per_day' in locals() else 2)
erotic_level = st.slider("エロ度（1: 控えめ → 10: 生々しい）", 1, 10, erotic_level if 'erotic_level' in locals() else 5)
tweet_length = st.slider("ツイート長（1: 短め → 10: 長め）", 1, 10, tweet_length if 'tweet_length' in locals() else 6)
question_frequency = st.slider("質問形式頻度（1: 稀 → 10: 多め）", 1, 10, question_frequency if 'question_frequency' in locals() else 4)
self_deprecation_level = st.slider("自己卑下度（1: 控えめ → 10: 強い）", 1, 10, self_deprecation_level if 'self_deprecation_level' in locals() else 5)
recruit_type = st.selectbox("募集タイプを選択", ["なし", "おじさん限定", "家出少女", "便器志願", "外国人アピール", "貧乳コンプ", "カスタム"], index=["なし", "おじさん限定", "家出少女", "便器志願", "外国人アピール", "貧乳コンプ", "カスタム"].index(recruit_type) if 'recruit_type' in locals() else 0)
custom_recruit = st.text_input("カスタム募集タイプを入力", value=custom_recruit if 'custom_recruit' in locals() else "") if recruit_type == "カスタム" else ""
col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns(9)
emoji_ban = col1.checkbox("絵文字禁止", value=emoji_ban if 'emoji_ban' in locals() else True)
hashtag_ban = col2.checkbox("ハッシュタグ禁止", value=hashtag_ban if 'hashtag_ban' in locals() else True)
newline_allow = col3.checkbox("改行を適切に使用", value=newline_allow if 'newline_allow' in locals() else True)
newline_ban = col4.checkbox("改行完全禁止", value=newline_ban if 'newline_ban' in locals() else False)
dm_invite = col5.checkbox("連絡誘導を入れる", value=dm_invite if 'dm_invite' in locals() else False)
sensitive_avoid = col6.checkbox("センシティブ回避（暗示表現）", value=sensitive_avoid if 'sensitive_avoid' in locals() else True)
fuzzy_mode = col7.checkbox("伏字モード", value=fuzzy_mode if 'fuzzy_mode' in locals() else False)
ellipsis_end = col8.checkbox("末尾に。。や...を入れる", value=ellipsis_end if 'ellipsis_end' in locals() else True)
dom_s_mode = col9.checkbox("ドSモード", value=dom_s_mode if 'dom_s_mode' in locals() else False)
generate_image_prompt = st.checkbox("ツイート連動画像プロンプトを作成", value=generate_image_prompt if 'generate_image_prompt' in locals() else True)
image_prompt_lang = st.selectbox("プロンプト言語", ["English", "Japanese"], index=0 if ('image_prompt_lang' in locals() and image_prompt_lang == "English") else 1)
mask_on = st.checkbox("白いマスク着用を追加", value=mask_on if 'mask_on' in locals() else True)
custom_rule = st.text_input("その他ルール", value=custom_rule if 'custom_rule' in locals() else "")

# キャラ設定CSV保存機能（追記対応）
st.subheader("キャラ設定保存")
char_name_save = st.text_input("保存するキャラ名（新規または既存）")
if st.button("現在の設定をCSVに追加保存"):
    if char_name_save:
        new_data = {
            "Character Name": [char_name_save],
            "Features": [features],
            "Reference": [reference],
            "Days": [days],
            "Tweets Per Day": [tweets_per_day],
            "Erotic Level": [erotic_level],
            "Tweet Length": [tweet_length],
            "Question Frequency": [question_frequency],
            "Self Deprecation Level": [self_deprecation_level],
            "Recruit Type": [recruit_type],
            "Custom Recruit": [custom_recruit],
            "Emoji Ban": [emoji_ban],
            "Hashtag Ban": [hashtag_ban],
            "Newline Allow": [newline_allow],
            "Newline Ban": [newline_ban],
            "DM Invite": [dm_invite],
            "Sensitive Avoid": [sensitive_avoid],
            "Fuzzy Mode": [fuzzy_mode],
            "Ellipsis End": [ellipsis_end],
            "Dom S Mode": [dom_s_mode],
            "Generate Image Prompt": [generate_image_prompt],
            "Image Prompt Lang": [image_prompt_lang],
            "Mask On": [mask_on],
            "Custom Rule": [custom_rule]
        }
        df_new = pd.DataFrame(new_data)
        csv_new = df_new.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="CSVダウンロード（現在のキャラ追加）",
            data=csv_new,
            file_name="characters_all.csv",
            mime="text/csv"
        )
        st.success("現在の設定をCSVに追加保存しました（ファイル名固定: characters_all.csv）。既存CSVとマージしてご利用ください")
    else:
        st.error("キャラ名を入力してください")

# 生成開始
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
        if ellipsis_end: rule_text += "ツイートの末尾や文中に「。。」「...」「．．．」などを適度に使用して余韻や切なさを演出。"
        if dom_s_mode: rule_text += "ドSな口調で上から目線・言葉責め・煽りを積極的に使用（例: 「おじさんならどうするの？」「満足させられる人だけ来て」など）。"
        rule_text += custom_rule

        # エロ度指示
        if erotic_level <= 3:
            erotic_instruction = "エロティックさは控えめで、直接的な表現を避け、雰囲気や暗示で表現。"
        elif erotic_level <= 6:
            erotic_instruction = "中程度のエロティック表現を使用。感覚的な描写を適度に取り入れる。"
        else:
            erotic_instruction = "生々しく大胆なエロティック表現を積極的に使用。具体的な描写も可。"

        # ツイート長指示
        if tweet_length <= 3:
            length_instruction = "ツイートは短め（100文字以内）で簡潔に。"
        elif tweet_length <= 6:
            length_instruction = "ツイートは中程度の長さ（150〜200文字程度）。"
        else:
            length_instruction = "ツイートは長め（220〜280文字）で詳細に描写。"

        # 重複禁止指示（強化版）
        repeat_prevention = "すべてのツイートで表現、シチュエーション、言い回しを多様化し、同じような内容やフレーズの繰り返しを厳禁とする。"

        reference_prompt = f"参考スタイル: {reference}" if reference else ""

        with st.spinner(f"{days}日分（{days * tweets_per_day}ツイート）生成中..."):
            today = datetime.date.today()
            dates = [today - datetime.timedelta(days=i) for i in range(days-1, -1, -1)]
            date_strings = [d.strftime("%Y-%m-%d") for d in dates]
            tweets = []
            image_prompts = []
            for i, date in enumerate(date_strings):
                prompt = f"""
                以下の指示で裏垢女子のツイートを1つ生成。
                - 特徴: {features}
                {reference_prompt}
                - 日付考慮: {date}頃の日常
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

                # 画像プロンプト生成（ツイート生成後に移動してtweetを使用可能に）
                image_prompt = ""
                if generate_image_prompt:
                    image_prompt_lang_text = "English" if image_prompt_lang == "English" else "Japanese"
                    mask_text = "wearing a white surgical face mask covering nose and mouth," if mask_on else ""
                    photo_style = "photorealistic, high resolution photo, natural indoor lighting, candid selfie style like taken with smartphone camera, realistic skin texture, detailed eyes and hair"
                    image_prompt_prompt = f"""
                    このツイート '{tweet}' に連動したX投稿用画像の詳細なプロンプトを作成。
                    - スタイル: {photo_style}
                    - Twitterセンシティブに引っかからない程度のエロさ（暗示的、服着用、雰囲気重視）
                    - 言語: {image_prompt_lang_text}
                    - 必ず含む: Japanese woman, age (estimated from {features}), breast size (estimated from {features}), {mask_text}
                    - 出力: プロンプト本文のみ
                    """
                    data_image = {
                        "model": model_name,
                        "messages": [{"role": "user", "content": image_prompt_prompt}],
                        "temperature": 0.8,
                        "max_tokens": 200
                    }
                    response_image = requests.post(API_URL, headers=headers, json=data_image)
                    if response_image.status_code == 200:
                        image_prompt = response_image.json()["choices"][0]["message"]["content"].strip()
                image_prompts.append(image_prompt)

            df = pd.DataFrame({"Date": date_strings, "Tweet": tweets, "Image Prompt": image_prompts})
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("CSVダウンロード", csv, "tweets.csv", "text/csv")
            st.dataframe(df)

st.info("生成時のみクレジット消費。初回は数円程度です。")
