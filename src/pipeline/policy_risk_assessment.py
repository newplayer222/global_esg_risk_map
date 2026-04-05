import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from dashscope import Generation
import json

# ==============================
# 自动设置项目根目录
# ==============================
def setup_project_root():
    script_path = os.path.abspath(sys.argv[0] if __name__ == "__main__" else __file__)
    current_dir = os.path.dirname(script_path)
    for _ in range(10):
        if (os.path.isdir(os.path.join(current_dir, 'data')) and 
            os.path.isdir(os.path.join(current_dir, 'src'))):
            os.chdir(current_dir)
            return
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
    raise RuntimeError("无法定位项目根目录！请确保脚本位于 global_esg_risk_map/ 目录结构中。")

setup_project_root()

# ==============================
# 配置
# ==============================
load_dotenv()
Generation.api_key = os.getenv("DASHSCOPE_API_KEY")

ESG_DATA_FILE = "data/intermediate/esg_risk_data.xlsx"
OUTPUT_SHEET = "policy_risk_assessment"

# 输出字段顺序（严格按你要求）
RISK_COLUMNS = [
    "policy_id",
    "policy_name",
    "country_cn",
    "country_en",
    "iso_alpha3",
    "分析时间",
    "合规成本",
    "业务影响",
    "执行不确定性",
    "时间紧迫性",
    "处罚严厉性",
    "base_risk",
    "sector",
    "topic"
]

# ==============================
# 调用 Qwen 进行风险评估
# ==============================
def assess_policy_risk(policy_record):
    prompt = f"""你是一位 ESG 风险分析师。请根据以下政策信息，对中国企业进行五维风险评估（每项 1-5 分，5 为最高风险）：

政策名称: {policy_record['policy_name']}
国家: {policy_record['country_en']}
行业: {policy_record['sector']}
议题: {policy_record['topic']}

请返回 JSON 格式，包含以下字段：
{{
  "合规成本": 整数（1-5）,
  "业务影响": 整数（1-5）,
  "执行不确定性": 整数（1-5）,
  "时间紧迫性": 整数（1-5）,
  "处罚严厉性": 整数（1-5）
}}

仅返回 JSON，不要任何解释。""".strip()

    response = Generation.call(
        model="qwen-turbo",
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
        temperature=0.2,
        max_tokens=200
    )
    
    if response.status_code != 200:
        raise Exception(f"Qwen API 错误: {response.code} - {response.message}")
    
    try:
        content = response.output.choices[0].message.content.strip()
        # 清理 Markdown JSON 块
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
        scores = json.loads(content)
        
        # 验证分数范围
        for key in ["合规成本", "业务影响", "执行不确定性", "时间紧迫性", "处罚严厉性"]:
            val = int(scores.get(key, 3))
            scores[key] = max(1, min(5, val))  # 强制 1-5
        return scores
    except Exception as e:
        raise Exception(f"JSON 解析失败: {str(e)}\n原始响应: {content}")

# ==============================
# 主函数：增量风险评估
# ==============================
def run_risk_assessment():
    print(f"📂 从 {ESG_DATA_FILE} 加载 policy_info 数据...")
    
    if not os.path.exists(ESG_DATA_FILE):
        raise FileNotFoundError(f"❌ 找不到 {ESG_DATA_FILE}，请先运行 policy_content_analyse.py")
    
    with pd.ExcelFile(ESG_DATA_FILE) as xls:
        if "policy_info" not in xls.sheet_names:
            raise ValueError("❌ 缺少 policy_info 表，请先生成政策内容分析")
        df_policy = pd.read_excel(xls, sheet_name="policy_info")
    
    print(f"📄 共加载 {len(df_policy)} 条待评估政策记录")
    
    # === 读取已存在的 risk assessment（用于去重）===
    existing_ids = set()
    all_sheets = {}
    
    if os.path.exists(ESG_DATA_FILE):
        try:
            with pd.ExcelFile(ESG_DATA_FILE) as xls:
                all_sheets = {name: pd.read_excel(xls, sheet_name=name) for name in xls.sheet_names}
                if OUTPUT_SHEET in all_sheets:
                    existing_df = all_sheets[OUTPUT_SHEET]
                    if not existing_df.empty and "policy_id" in existing_df.columns and "sector" in existing_df.columns and "topic" in existing_df.columns:
                        # 使用 (policy_id, sector, topic) 三元组去重
                        existing_ids = set(
                            existing_df[['policy_id', 'sector', 'topic']]
                            .apply(lambda x: f"{x['policy_id']}|{x['sector']}|{x['topic']}", axis=1)
                        )
                        print(f"📌 检测到已有 {len(existing_ids)} 条风险评估记录，将跳过重复项")
        except Exception as e:
            print(f"⚠️ 读取现有 risk assessment 失败: {e}")

    # === 开始评估 ===
    results = []
    analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for idx, row in df_policy.iterrows():
        # 构建唯一键
        unique_key = f"{row['policy_id']}|{row['sector']}|{row['topic']}"
        if unique_key in existing_ids:
            continue
        
        print(f"\n🔍 评估 [{idx+1}/{len(df_policy)}]: {row['policy_name']} | {row['sector']} | {row['topic']}")
        
        try:
            scores = assess_policy_risk(row.to_dict())
            
            # 计算 base_risk（简单平均，可替换为加权）
            base_risk = round(sum(scores.values()) / 5.0, 2)
            
            record = {
                "policy_id": row["policy_id"],
                "policy_name": row["policy_name"],
                "country_cn": row["country_cn"],
                "country_en": row["country_en"],
                "iso_alpha3": row["iso_alpha3"],
                "分析时间": analysis_time,
                "合规成本": scores["合规成本"],
                "业务影响": scores["业务影响"],
                "执行不确定性": scores["执行不确定性"],
                "时间紧迫性": scores["时间紧迫性"],
                "处罚严厉性": scores["处罚严厉性"],
                "base_risk": base_risk,
                "sector": row["sector"],
                "topic": row["topic"]
            }
            results.append(record)
            print(f"✅ 评分完成: base_risk={base_risk}")
            
        except Exception as e:
            print(f"❌ 跳过: {e}")

    # === 合并并保存 ===
    final_df = pd.DataFrame(columns=RISK_COLUMNS)
    
    # 1. 加载现有数据（如果存在）
    if OUTPUT_SHEET in all_sheets:
        final_df = all_sheets[OUTPUT_SHEET]
        # 确保列顺序正确
        final_df = final_df[RISK_COLUMNS]
    
    # 2. 添加新数据
    if results:
        new_df = pd.DataFrame(results)
        new_df = new_df[RISK_COLUMNS]  # 强制列顺序
        final_df = pd.concat([final_df, new_df], ignore_index=True)
        print(f"\n🆕 新增 {len(new_df)} 条风险评估记录")
    
    # 3. 更新 sheets
    all_sheets[OUTPUT_SHEET] = final_df
    
    # 4. 写回原文件（保留所有 sheets）
    with pd.ExcelWriter(ESG_DATA_FILE, engine='openpyxl') as writer:
        for sheet_name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"\n🎉 风险评估完成！共 {len(final_df)} 条记录保存至 '{ESG_DATA_FILE}' 的 '{OUTPUT_SHEET}' 表。")

# ==============================
# 入口
# ==============================
if __name__ == "__main__":
    run_risk_assessment()