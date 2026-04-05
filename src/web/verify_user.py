# verify_user.py
import pandas as pd
import os

def verify_user(account, code):
    file_path = os.path.join(os.getcwd(), 'data', 'credentials', 'users.xlsx')
    if not os.path.exists(file_path):
        print("❌ users.xlsx 文件不存在！")
        return False

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"❌ 读取 Excel 失败: {e}")
        return False

    # 清理数据：转字符串 + 去除首尾空格
    df['account'] = df['account'].astype(str).str.strip()
    df['code'] = df['code'].astype(str).str.strip()

    # 清理输入
    account_clean = str(account).strip()
    code_clean = str(code).strip()

    # 匹配
    matched = df[
        (df['account'] == account_clean) &
        (df['code'] == code_clean)
    ]

    return len(matched) > 0
