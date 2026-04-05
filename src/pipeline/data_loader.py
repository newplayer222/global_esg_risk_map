import pandas as pd
import os

def load_basic_data():
    """加载基础数据"""
    # 从项目根目录查找
    current_dir = os.path.dirname(__file__)
    for _ in range(5):  # 最多向上找5层
        project_root = os.path.dirname(current_dir)
        data_file = os.path.join(project_root, "data", "input", "basic_data.xlsx")
        if os.path.exists(data_file):
            sheets = ["country_list", "topic_list", "sector_list", "sector_correlation"]
            return {sheet: pd.read_excel(data_file, sheet_name=sheet) for sheet in sheets}
        current_dir = project_root
    raise FileNotFoundError("Could not find basic_data.xlsx in data/input/")
