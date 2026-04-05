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

# 输出字段顺序（严格按你要求）
OUTPUT_COLUMNS = [
    "country_cn",
    "country_en",
    "iso_alpha3",
    "topic",
    "sector",
    "total_risk"
]

# ==============================
# 主函数
# ==============================
def main():
    if not os.path.exists(ESG_DATA_FILE):
        raise FileNotFoundError(f"❌ 找不到文件: {ESG_DATA_FILE}，请先运行前面的 pipeline 步骤")

    print("🔍 正在读取 policy_total_risk 表...")
    df_policy_total = pd.read_excel(ESG_DATA_FILE, sheet_name="policy_total_risk")

    # === 按 (country_cn, topic, sector) 聚合并求平均 ===
    df_aggregated = df_policy_total.groupby(
        ['country_cn', 'country_en', 'iso_alpha3', 'topic', 'sector']
    )['policy_total_risk'].mean().reset_index()

    # 重命名风险列
    df_aggregated.rename(columns={'policy_total_risk': 'total_risk'}, inplace=True)

    # 四舍五入到两位小数
    df_aggregated['total_risk'] = df_aggregated['total_risk'].round(2)

    # 强制列顺序
    df_aggregated = df_aggregated[OUTPUT_COLUMNS]

    print(f"✅ 成功聚合 {len(df_aggregated)} 条记录")

    # === 【关键修改】只更新 total_risk 表，保留其他所有 sheets ===
    with pd.ExcelFile(ESG_DATA_FILE) as xls:
        all_sheets = {name: pd.read_excel(xls, sheet_name=name) for name in xls.sheet_names}

    # 替换或新增 total_risk
    all_sheets['total_risk'] = df_aggregated

    # 写回原文件（覆盖整个 Excel，但保留所有 sheets 内容）
    with pd.ExcelWriter(ESG_DATA_FILE, engine='openpyxl') as writer:
        for name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)

    print(f"🎉 total_risk 表已成功生成并保存至 '{ESG_DATA_FILE}'！")

# ==============================
# 入口
# ==============================
if __name__ == "__main__":
    main()