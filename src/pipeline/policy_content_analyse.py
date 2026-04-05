import os
import sys
import pandas as pd
import itertools
import re
from difflib import get_close_matches
from dotenv import load_dotenv
from dashscope import Generation

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

BASIC_DATA_FILE = "data/input/basic_data.xlsx"
POLICY_LINKS_FILE = "data/intermediate/policy_link.xlsx"
OUTPUT_FILE = "data/intermediate/esg_risk_data.xlsx"

# 确保输出目录存在
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

# ==============================
# 辅助函数：标准化 sector/topic
# ==============================
def split_multivalue(text):
    """拆分多值字符串（支持 , ; ， ； \n 等分隔符）"""
    if pd.isna(text) or str(text).strip() == "":
        return []
    parts = re.split(r'[;,，；\n]', str(text))
    return [p.strip() for p in parts if p.strip()]

def normalize_to_valid(value, valid_set, fallback_value=None, label=""):
    """将模型输出标准化到有效集合，支持模糊匹配"""
    if not value or value.lower() in ["nan", "none", "null", ""]:
        return None
        
    candidates = split_multivalue(value)
    normalized = []
    
    for cand in candidates:
        # 1. 精确匹配
        if cand in valid_set:
            normalized.append(cand)
            continue
            
        # 2. 模糊匹配（相似度 > 0.6）
        close_match = get_close_matches(cand, valid_set, n=1, cutoff=0.6)
        if close_match:
            print(f"🔍 模糊匹配: '{cand}' → '{close_match[0]}'")
            normalized.append(close_match[0])
        else:
            print(f"⚠️ 无效{label}: '{cand}'（不在白名单中）")
    
    return normalized if normalized else None

# ==============================
# 加载基础数据
# ==============================
def load_basic_data():
    print(f"📂 从 {BASIC_DATA_FILE} 加载基础数据...")
    
    # 加载国家数据（使用列名访问）
    country_df = pd.read_excel(BASIC_DATA_FILE, sheet_name="country_list")
    countries = []
    for _, row in country_df.iterrows():
        country_en = str(row["country_en"]).strip()
        country_cn = str(row["country_cn"]).strip()
        if country_en and country_cn and country_en.lower() != 'nan':
            countries.append((country_en, country_cn))
    
    # 加载议题数据
    topic_df = pd.read_excel(BASIC_DATA_FILE, sheet_name="topic_list")
    topics = [str(t).strip() for t in topic_df.iloc[:, 0].dropna() if str(t).strip()]
    
    # 加载行业数据
    sector_df = pd.read_excel(BASIC_DATA_FILE, sheet_name="sector_list")
    sectors = [str(s).strip() for s in sector_df.iloc[:, 0].dropna() if str(s).strip()]
    
    valid_countries = set([cn[0] for cn in countries])
    valid_topics = set(topics)
    valid_sectors = set(sectors)
    country_map = dict(countries)
    
    print(f"✅ 加载完成: {len(valid_countries)} 国家, {len(valid_topics)} 议题, {len(valid_sectors)} 行业")
    return {
        "valid_countries": valid_countries,
        "valid_topics": valid_topics,
        "valid_sectors": valid_sectors,
        "country_map": country_map
    }

# ==============================
# 调用 Qwen 分析政策
# ==============================
def call_qwen_for_policy_analysis(policy_info, all_topics, all_sectors):
    prompt = f"""你是一位 ESG 政策专家。请根据以下政策信息，严格按 JSON 格式返回分析结果：
- effective_date: 生效日期 (YYYY-MM-DD)
- implementation_date: 执行日期 (YYYY-MM-DD)
- key_provisions: 主要规定（用中文分号分隔的列表字符串，如 "规定1；规定2"）
- application_scope: 适用范围（中文描述）
- major_impact: 对中国企业的影响（中文描述）
- influenced_sector: 影响的行业（可多个，用中文分号分隔，必须来自以下列表：{list(all_sectors)})
- related_topic: 相关ESG议题（可多个，用中文分号分隔，必须来自以下列表：{list(all_topics)})

政策名称: {policy_info['policy_name']}
国家: {policy_info['country_en']}
链接: {policy_info['link']}

请确保：
1. 日期格式严格为 YYYY-MM-DD
2. influenced_sector 和 related_topic 必须是给定列表中的值或其子集
3. 不添加任何额外字段或解释""".strip()

    response = Generation.call(
        model="qwen-max",
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
        temperature=0.0,
        max_tokens=1000
    )
    if response.status_code != 200:
        raise Exception(f"Qwen API 错误: {response.code} - {response.message}")
    
    try:
        import json
        content = response.output.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
        return json.loads(content)
    except Exception as e:
        raise Exception(f"JSON 解析失败: {str(e)}\n原始响应: {content}")

# ==============================
# 主分析函数
# ==============================
def analyse_policies():
    basic_data = load_basic_data()
    valid_countries = basic_data["valid_countries"]
    valid_topics = basic_data["valid_topics"]
    valid_sectors = basic_data["valid_sectors"]
    country_map = basic_data["country_map"]

    print(f"📄 从 {POLICY_LINKS_FILE} 加载政策链接...")
    df_links = pd.read_excel(POLICY_LINKS_FILE)
    print(f"📄 共加载 {len(df_links)} 条政策链接")

    # === 读取已存在的 policy_info 数据（用于去重）===
    existing_policy_ids = set()
    existing_df = None
    all_sheets = {}

    if os.path.exists(OUTPUT_FILE):
        try:
            with pd.ExcelFile(OUTPUT_FILE) as xls:
                all_sheets = {name: pd.read_excel(xls, sheet_name=name) for name in xls.sheet_names}
                if "policy_info" in all_sheets:
                    existing_df = all_sheets["policy_info"]
                    if not existing_df.empty and "policy_id" in existing_df.columns:
                        existing_policy_ids = set(existing_df["policy_id"].dropna().astype(str))
                        print(f"📌 检测到已有 {len(existing_policy_ids)} 条已分析政策，将跳过重复项")
        except Exception as e:
            print(f"⚠️ 读取现有 {OUTPUT_FILE} 失败: {e}")

    results = []
    policy_cache = {}

    for idx, row in df_links.iterrows():
        policy_id = str(row["policy_id"]).strip()
        if policy_id in existing_policy_ids:
            print(f"⏭️ 跳过已分析政策: {policy_id} - {row['policy_name']}")
            continue

        country_en = str(row["country_en"]).strip()
        if not country_en or country_en.lower() == "nan":
            print(f"⚠️ 跳过无效国家政策: {row['policy_name']}")
            continue
        if country_en not in valid_countries:
            print(f"⚠️ 跳过非法国家政策: {row['policy_name']} ({country_en})")
            continue

        country_cn = country_map.get(country_en, country_en)
        iso_alpha3 = row.get("iso_alpha3", "") if "iso_alpha3" in row else ""

        policy_info = {
            "policy_id": policy_id,
            "policy_name": str(row["policy_name"]),
            "country_en": country_en,
            "link": str(row["link"]),
            "record_date": str(row["record_date"])
        }

        cache_key = f"{policy_info['policy_name']}|{policy_info['country_en']}"
        print(f"\n🔍 分析 [{idx+1}/{len(df_links)}]: {policy_info['policy_name']} ({country_en})")

        try:
            if cache_key in policy_cache:
                analysis = policy_cache[cache_key]
                print(f"📦 使用缓存结果")
            else:
                analysis = call_qwen_for_policy_analysis(policy_info, valid_topics, valid_sectors)
                policy_cache[cache_key] = analysis
                print(f"☁️ 调用 Qwen 成功")

            # === 标准化 sector 和 topic（关键修复）===
            sectors_raw = analysis.get("influenced_sector", "")
            topics_raw = analysis.get("related_topic", "")

            sectors_list = normalize_to_valid(sectors_raw, valid_sectors, label="行业") or ["综合"] if "综合" in valid_sectors else [next(iter(valid_sectors))]
            topics_list = normalize_to_valid(topics_raw, valid_topics, label="议题") or [next(iter(valid_topics))] if valid_topics else ["综合ESG风险"]

            # === 笛卡尔积生成记录 ===
            for sector, topic in itertools.product(sectors_list, topics_list):
                expanded_record = {
                    "policy_id": policy_info["policy_id"],
                    "policy_name": policy_info["policy_name"],
                    "country_cn": country_cn,
                    "country_en": policy_info["country_en"],
                    "iso_alpha3": iso_alpha3,
                    "link": policy_info["link"],
                    "record_date": policy_info["record_date"],
                    "effective_date": str(analysis.get("effective_date", "")),
                    "implementation_date": str(analysis.get("implementation_date", "")),
                    "key_provisions": str(analysis.get("key_provisions", "")),
                    "application_scope": str(analysis.get("application_scope", "")),
                    "major_impact": str(analysis.get("major_impact", "")),
                    "sector": sector,
                    "topic": topic
                }
                results.append(expanded_record)
            print(f"✅ 成功: 拆分为 {len(sectors_list) * len(topics_list)} 条记录")

        except Exception as e:
            print(f"❌ 跳过: {e}")

    # === 合并新旧数据并保存（保留所有 sheets）===
    FINAL_COLUMNS = [
        "policy_id", "policy_name", "country_cn", "country_en", "iso_alpha3", "link", "record_date",
        "effective_date", "implementation_date", "key_provisions", "application_scope", "major_impact", "sector", "topic"
    ]
    
    final_df = existing_df if existing_df is not None else pd.DataFrame(columns=FINAL_COLUMNS)
    
    if results:
        new_df = pd.DataFrame(results)
        # 强制列顺序与目标一致
        new_df = new_df[FINAL_COLUMNS]
        final_df = pd.concat([final_df, new_df], ignore_index=True)
        print(f"\n🆕 新增 {len(new_df)} 条记录")

    # 更新 policy_info sheet，其他 sheets 保持不变
    all_sheets["policy_info"] = final_df

    # 写回原文件（覆盖整个 Excel，但保留所有 sheets）
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        for sheet_name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"\n🎉 保存成功! 当前共 {len(final_df)} 条记录在 '{OUTPUT_FILE}' 的 'policy_info' 表中。")

# ==============================
# 入口
# ==============================
if __name__ == "__main__":
    analyse_policies()