import os
import sys
import pandas as pd

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
# 配置路径
# ==============================
ESG_DATA_FILE = "data/intermediate/esg_risk_data.xlsx"
BASIC_DATA_FILE = "data/input/basic_data.xlsx"

# 输出字段顺序（严格按你要求）
OUTPUT_COLUMNS = [
    "policy_id",
    "country_cn",
    "country_en",
    "iso_alpha3",
    "sector",
    "topic",
    "policy_total_risk"
]

# ==============================
# 主函数
# ==============================
def main():
    # 1. 读取数据
    print(f"📂 从 {ESG_DATA_FILE} 加载 policy_risk_assessment...")
    policy_assessment = pd.read_excel(ESG_DATA_FILE, sheet_name="policy_risk_assessment")
    
    print(f"📂 从 {BASIC_DATA_FILE} 加载 sector_correlation 和 country_list...")
    sector_corr = pd.read_excel(BASIC_DATA_FILE, sheet_name="sector_correlation")
    country_list_df = pd.read_excel(BASIC_DATA_FILE, sheet_name="country_list")

    # 2. 构建国家映射 (英文名 -> 完整信息)
    country_map = {}
    for _, row in country_list_df.iterrows():
        cn = str(row["country_cn"]).strip()
        en = str(row["country_en"]).strip()
        iso = str(row["iso_alpha3"]).strip()
        if cn and en and iso and en.lower() != 'nan':
            country_map[en] = {"country_cn": cn, "country_en": en, "iso_alpha3": iso}

    results = []

    # 3. 遍历每条风险评估记录
    for _, row in policy_assessment.iterrows():
        policy_id = row["policy_id"]
        country_cn = str(row["country_cn"]).strip()
        topic = row["topic"]
        base_risk = float(row["base_risk"])
        sector_from_assessment = row["sector"]

        # 获取标准化国家信息
        country_info = country_map.get(country_cn, {
            "country_cn": country_cn,
            "country_en": "Unknown",
            "iso_alpha3": "XXX"
        })

        # 从 sector_correlation 查找相关性
        corr_row = sector_corr[
            (sector_corr["topic"] == topic) & 
            (sector_corr["sector"] == sector_from_assessment)
        ]
        correlation = float(corr_row.iloc[0]["correlation"]) if not corr_row.empty else 0.0

        total_risk = base_risk * correlation

        results.append({
            "policy_id": policy_id,
            "country_cn": country_info["country_cn"],
            "country_en": country_info["country_en"],
            "iso_alpha3": country_info["iso_alpha3"],
            "sector": sector_from_assessment,
            "topic": topic,
            "policy_total_risk": round(total_risk, 2)
        })

    # 4. 构建输出 DataFrame
    output_df = pd.DataFrame(results, columns=OUTPUT_COLUMNS)

    # 5. 【关键修改】只更新 policy_total_risk 表，保留其他所有 sheets
    from openpyxl import load_workbook

    if not os.path.exists(ESG_DATA_FILE):
        raise FileNotFoundError(f"❌ {ESG_DATA_FILE} 不存在，请先生成 policy_risk_assessment")

    # 读取所有现有 sheets
    with pd.ExcelFile(ESG_DATA_FILE) as xls:
        all_sheets = {name: pd.read_excel(xls, sheet_name=name) for name in xls.sheet_names}

    # 替换或新增 policy_total_risk
    all_sheets["policy_total_risk"] = output_df

    # 写回整个文件（安全方式：使用 openpyxl 引擎）
    with pd.ExcelWriter(ESG_DATA_FILE, engine='openpyxl', mode='w') as writer:
        for sheet_name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"✅ 成功生成 {len(output_df)} 条 policy_total_risk 记录，已保存至 '{ESG_DATA_FILE}' 的 'policy_total_risk' 表。")

# ==============================
# 入口
# ==============================
if __name__ == "__main__":
    main()