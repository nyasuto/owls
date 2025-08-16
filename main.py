# pip install pyautogen
import autogen
import datetime
import os
import requests
import sys

# サーバー接続確認機能
def check_server_connection(base_url):
    try:
        print(f"LM Studioサーバー接続確認中: {base_url}")
        response = requests.get(f"{base_url}/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print(f"✅ サーバー接続成功! 利用可能モデル数: {len(models.get('data', []))}")
            return True
        else:
            print(f"❌ サーバー応答エラー: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ LM Studioサーバーに接続できません")
        print("   1. LM Studioを起動してください")
        print("   2. ローカルサーバーが http://localhost:1234 で動作していることを確認してください")
        return False
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False

CFG = {
    "model": "openai/gpt-oss-20b",
    "api_key": "lm-studio",
    "base_url": "http://localhost:1234/v1",
    "temperature": 0.9,
    "max_tokens": 80480,
}

# サーバー接続確認
if not check_server_connection(CFG["base_url"]):
    print("\n🔧 解決方法:")
    print("1. LM Studioアプリケーションを起動")
    print("2. モデルをロードして 'Start Server' をクリック")
    print("3. サーバーが http://localhost:1234 で起動していることを確認")
    sys.exit(1)

pro = autogen.AssistantAgent(
    name="Pro",
    system_message=(
        "あなたはPlan Aの長所と可能性を最大化して主張する役割。Plan Bの弱点とリスクを鋭く指摘する役割。"
        "他の参加者の発言を受けて、さらに深い議論を展開し、反論や追加の論点を提示してください。"
        "必ず日本語で応答してください。英語は使用しないでください。"
    ),
    llm_config=CFG,
)

con = autogen.AssistantAgent(
    name="Con",
    system_message=(
        "あなたはPlan Bの長所と可能性を最大化して主張。Plan Aの弱点とリスクを鋭く指摘する役割。"
        "他の参加者の発言を受けて、さらに深い議論を展開し、反論や追加の論点を提示してください。"
        "必ず日本語で応答してください。英語は使用しないでください。"
    ),
    llm_config=CFG,
)

mediator = autogen.AssistantAgent(
    name="Mediator",
    system_message=(
        "あなたは調停役。ProとConの主張を統合し、議論を深めていく役割です。"
        "最終ラウンドでは、両者の要素を最低1つずつ残し、さらに新規要素を1つ以上加えた第三案を必ず提示。"
        "最後は3つの箇条書き:『残した長所』『回避したリスク』『新規要素』で締める。"
        "途中のラウンドでは、争点を整理し、さらなる論点を引き出してください。"
        "必ず日本語で応答してください。英語は使用しないでください。"
    ),
    llm_config=CFG,
)

# UserProxyAgentを追加
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    default_auto_reply="TERMINATE",
    code_execution_config=False,
)

# GroupChatとGroupChatManagerを設定
groupchat = autogen.GroupChat(
    agents=[pro, con, mediator],
    messages=[],
    max_round=9,  # 3ラウンド × 3人 = 9回
    speaker_selection_method="round_robin"
)

manager = autogen.GroupChatManager(
    groupchat=groupchat,
    llm_config=CFG
)

# 複数ラウンドの議論を開始
topic = "Plan A 原子力発電推進 vs Plan B 再生可能エネルギー集中"
initial_message = f"テーマ: {topic}\n\n3ラウンドの議論を行います。Pro、Con、Mediatorの順番で発言してください。"

# 議論開始時刻を記録
start_time = datetime.datetime.now()
print(f"\n🎯 議論開始: {topic}")
print(f"⏰ 開始時刻: {start_time.strftime('%Y年%m月%d日 %H:%M:%S')}")
print("=" * 60)

try:
    # 正しいAutoGenの使い方: UserProxyAgentのinitiate_chatを使用
    chat_result = user_proxy.initiate_chat(
        manager,
        message=initial_message,
        clear_history=True,
    )
    
    # 議論終了時刻を記録
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    
    print(f"\n✅ 議論完了! 総メッセージ数: {len(groupchat.messages)}")
    print(f"⏰ 終了時刻: {end_time.strftime('%Y年%m月%d日 %H:%M:%S')}")
    print(f"⌛ 議論時間: {duration.total_seconds():.1f}秒 ({duration.seconds // 60}分{duration.seconds % 60}秒)")
    
except Exception as e:
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    print(f"❌ 議論中にエラーが発生: {e}")
    print(f"⌛ エラーまでの時間: {duration.total_seconds():.1f}秒")
    print("LM Studioサーバーの状態を確認してください")

# 議論内容をMarkdownファイルに保存
def save_chat_to_markdown(groupchat, topic, start_time, end_time, duration):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"debate_{timestamp}.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# AI議論セッション\n\n")
        f.write(f"**テーマ:** {topic}\n\n")
        f.write(f"**開始時刻:** {start_time.strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")
        f.write(f"**終了時刻:** {end_time.strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")
        f.write(f"**議論時間:** {duration.total_seconds():.1f}秒 ({duration.seconds // 60}分{duration.seconds % 60}秒)\n\n")
        f.write(f"**参加エージェント:** Pro (Plan A支持), Con (Plan B支持), Mediator (調停役)\n\n")
        f.write(f"**総メッセージ数:** {len(groupchat.messages)}\n\n")
        f.write("---\n\n")
        
        for i, message in enumerate(groupchat.messages, 1):
            speaker = message.get('name', 'Unknown')
            content = message.get('content', '')
            f.write(f"## 発言 {i}: {speaker}\n\n")
            f.write(f"{content}\n\n")
            f.write("---\n\n")
    
    print(f"\n📄 議論内容を {filename} に保存しました。")
    return filename

# 議論終了後にMarkdownファイルに保存
if 'end_time' in locals() and 'duration' in locals():
    saved_file = save_chat_to_markdown(groupchat, topic, start_time, end_time, duration)
else:
    # エラーの場合
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    saved_file = save_chat_to_markdown(groupchat, topic, start_time, end_time, duration)