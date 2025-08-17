# pip install pyautogen
import autogen

CFG = {
    "model": "lmstudio-local",  # 任意ラベル
    "api_key": "lm-studio",
    "base_url": "http://localhost:1234/v1",
    "temperature": 0.9,
    "max_tokens": 2048,
}

pro = autogen.AssistantAgent(
    name="Pro",
    system_message="あなたは提案の長所と可能性を最大化して主張する役割。",
    llm_config=CFG,
)

con = autogen.AssistantAgent(
    name="Con",
    system_message="あなたは提案の弱点とリスクを鋭く指摘する役割。",
    llm_config=CFG,
)

mediator = autogen.AssistantAgent(
    name="Mediator",
    system_message=(
        "あなたは調停役。ProとConの主張を統合し、"
        "両者の要素を最低1つずつ残し、さらに新規要素を1つ以上加えた第三案を必ず提示。"
        "最後は3つの箇条書き:『残した長所』『回避したリスク』『新規要素』で締める。"
    ),
    llm_config=CFG,
)

# コーディネート（1ラウンド例）
topic = "都心の主要エリアを『平日昼の自家用車通行禁止』にするべきか？"
pro_msg = pro.generate_reply(
    messages=[{"role": "user", "content": f"テーマ: {topic}。強く賛成の立場で論じて。"}]
)
con_msg = con.generate_reply(
    messages=[{"role": "user", "content": f"テーマ: {topic}。強く反対の立場で論じて。"}]
)
final = mediator.generate_reply(
    messages=[
        {
            "role": "user",
            "content": f"Proの主張:\n{pro_msg['content']}\n\nConの主張:\n{con_msg['content']}\n\n統合案を出して。",
        }
    ]
)

print(final["content"])
