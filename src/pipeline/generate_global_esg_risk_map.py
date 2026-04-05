#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import pandas as pd
from jinja2 import Template
from pathlib import Path

# ==============================
# 自动设置项目根目录（支持从任意位置调用）
# ==============================
def setup_project_root():
    script_dir = Path(__file__).resolve().parent  # pipeline/
    project_root = script_dir.parent.parent       # global_esg_risk_map/
    os.chdir(project_root)
    sys.path.insert(0, str(project_root))

setup_project_root()

# ==============================
# 文件路径配置（明确指向 data/ 目录）
# ==============================
EXCEL_FILE = os.path.join("data","intermediate", "esg_risk_data.xlsx")
BASIC_DATA_FILE = os.path.join("data","input", "basic_data.xlsx")

# ==============================
# 主函数
# ==============================
def main():
    print("🔍 正在读取 Excel 文件...")
    
    # === 1. 从 policy_info 获取完整的政策信息（包含 topic）===
    df_policy_info = pd.read_excel(EXCEL_FILE, sheet_name="policy_info")

    df_policy_info = df_policy_info.drop_duplicates(
    subset=["policy_id", "country_en", "sector", "topic"],
    keep="first"  # 保留第一条
    )
    
    # === 2. 从 basic_data 获取国家、行业、议题列表 ===
    country_mapping_df = pd.read_excel(BASIC_DATA_FILE, sheet_name="country_list")
    en_to_cn = {}
    for _, row in country_mapping_df.iterrows():
        country_cn = str(row["country_cn"]).strip()
        country_en = str(row["country_en"]).strip()
        if country_cn and country_en and country_en.lower() != 'nan':
            en_to_cn[country_en] = country_cn
    
    # 读取所有可能的行业和议题
    all_countries = country_mapping_df["country_en"].dropna().unique().tolist()
    try:
        sector_df = pd.read_excel(BASIC_DATA_FILE, sheet_name="sector_list")
        all_sectors = sector_df["sector"].dropna().unique().tolist()
    except:
        all_sectors = []  # 如果没有表，设为空
    
    try:
        topic_df = pd.read_excel(BASIC_DATA_FILE, sheet_name="topic_list")
        all_topics = topic_df["topic"].dropna().unique().tolist()
    except:
        all_topics = []  # 如果没有表，设为空
    
    # === 3. 准备风险数据：创建全组合，缺失的设为 -1 ===
    # 先创建所有国家-行业-议题的笛卡尔积
    if all_sectors and all_topics:
        full_combinations = pd.DataFrame([
            {"Country_EN": c, "Sector": s, "Topic": t, "Risk": -1}
            for c in all_countries
            for s in all_sectors
            for t in all_topics
        ])
    else:
        full_combinations = pd.DataFrame(columns=["Country_EN", "Sector", "Topic", "Risk"])
    
    # 实际数据
    df_policy_total = pd.read_excel(EXCEL_FILE, sheet_name="policy_total_risk")
    df_merged = pd.merge(
        df_policy_info,
        df_policy_total[["policy_id", "policy_total_risk"]],
        on="policy_id",
        how="inner"
    )
    actual_df = df_merged.rename(columns={
        "country_en": "Country_EN",
        "sector": "Sector",
        "topic": "Topic",
        "policy_total_risk": "Risk"
    })[["Country_EN", "Sector", "Topic", "Risk"]]
    
    # 合并：用实际数据覆盖默认 -1
    if not full_combinations.empty:
        df_risk = pd.merge(
            full_combinations,
            actual_df,
            on=["Country_EN", "Sector", "Topic"],
            how="left",
            suffixes=("", "_actual")
        )
        df_risk["Risk"] = df_risk["Risk_actual"].fillna(df_risk["Risk"])
        df_risk = df_risk.drop(columns=["Risk_actual"])
    else:
        df_risk = actual_df
    
    # 添加中文国家名
    df_risk["Country_ZH"] = df_risk["Country_EN"].map(en_to_cn).fillna(df_risk["Country_EN"])
    
    print(f"✅ 成功加载 {len(df_risk)} 条风险记录（包含缺失数据设为 -1）")

    # === 4. 准备政策详情数据（就是 df_policy_info 本身）===
    df_policy = df_policy_info.rename(columns={
        "country_en": "Country_EN",
        "topic": "Topic",
        "policy_name": "政策法规名称",
        "effective_date": "生效时间",
        "implementation_date": "执行时间",
        "key_provisions": "主要规定",
        "application_scope": "适用范围",
        "major_impact": "对中国企业的影响",
        "sector": "Sector"
    })
    df_policy["Country_ZH"] = df_policy["Country_EN"].map(en_to_cn).fillna(df_policy["Country_EN"])

    # === 5. 提取维度（使用完整列表）===
    esg_topics = sorted(all_topics) if all_topics else sorted(df_risk["Topic"].dropna().unique().tolist())
    gics_sectors = sorted(all_sectors) if all_sectors else sorted(df_risk["Sector"].dropna().unique().tolist())
    default_selected_topics = esg_topics[:3] if len(esg_topics) > 3 else esg_topics

    # === 6. 构建政策字典 (Country_ZH|Topic|Sector → 政策列表)，为全组合初始化空列表 ===
    policy_dict = {}
    # 先为所有组合初始化空列表
    for country in all_countries:
        country_zh = en_to_cn.get(country, country)
        for sector in gics_sectors:
            for topic in esg_topics:
                key = f"{country_zh}|{topic}|{sector}"
                policy_dict[key] = []
    
    # 然后添加实际政策
    for _, row in df_policy.iterrows():
        key = f"{row['Country_ZH']}|{row['Topic']}|{row['Sector']}"
        policy = {
            "政策法规名称": str(row.get("政策法规名称", "")),
            "生效时间": str(row.get("生效时间", "")),
            "执行时间": str(row.get("执行时间", "")),
            "主要规定": str(row.get("主要规定", "")),
            "适用范围": str(row.get("适用范围", "")),
            "对中国企业的影响": str(row.get("对中国企业的影响", ""))
        }
        policy_dict.setdefault(key, []).append(policy)

    policy_json_str = json.dumps(policy_dict, ensure_ascii=False)

    # === 7. HTML 模板（保持不变）===
    html_template_str = '''<!DOCTYPE html>
<html lang="zh">
<head>
 <meta charset="UTF-8">
 <meta name="viewport" content="width=device-width, initial-scale=1.0">
 <title>全球ESG风险地图（分行业、分议题、分国别）</title>
 <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
 <style>
 body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif; margin: 0; padding: 20px; background-color: #f7f9fc; color: #333; font-size: 14px; }
 .page-title { text-align: center; font-size: 28px; font-weight: bold; color: #2c3e50; margin-bottom: 25px; padding-bottom: 12px; border-bottom: 2px solid #ddd; }
 .container { display: flex; gap: 20px; min-height: 100vh; }
 .sidebar { width: 220px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); height: fit-content; position: sticky; top: 20px; }
 .main-content { flex: 1; display: flex; gap: 20px; }
 .map-area { flex: 1; min-width: 0; }
 .info-panel { width: 260px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); height: fit-content; position: sticky; top: 20px; }
 .info-panel h3 { margin-top: 0; color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 8px; text-align: left; }
 .info-item { margin-bottom: 12px; text-align: left; }
 .info-label { font-weight: bold; color: #555; display: inline-block; width: 120px; margin-right: 8px; vertical-align: top; }
 .info-value { color: #222; word-wrap: break-word; }
 .empty-info { color: #888; font-style: italic; text-align: left; padding: 20px 0; }
 .sidebar h3 { margin: 0 0 8px 0; color: #2c3e50; font-size: 16px; }
 .notice { background: #fff8e1; padding: 10px; border-radius: 4px; font-size: 13px; margin-bottom: 15px; }
 .topic-label { display: flex; align-items: center; gap: 8px; margin: 4px 0; cursor: pointer; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%; }
 .topic-checkbox { width: 16px; height: 16px; margin: 0; }
 select#sector-select { width: 100%; padding: 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; margin-bottom: 16px; }
 .map-container { width: 100%; height: auto; position: relative; }
 .empty-message { padding: 40px; text-align: center; color: #888; }
 </style>
</head>
<body>
 <div class="page-title">全球ESG风险地图（分行业、分议题、分国别）</div>
 <div class="container">
 <div class="sidebar">
 <div class="notice">💡 默认显示前3个议题，可自由多选所有议题</div>
 <h3>行业筛选</h3>
 <select id="sector-select">
 {% for sector in gics_sectors %}
 <option value="{{ sector }}">{{ sector }}</option>
 {% endfor %}
 </select>
 <h3>ESG 议题</h3>
 <label class="topic-label" style="font-weight:normal;margin-bottom:4px;">
 <input type="checkbox" id="select-all-topics" class="topic-checkbox"> 全选
 </label>
 {% for topic in esg_topics %}
 <label class="topic-label">
 <input type="checkbox" class="topic-checkbox" value="{{ topic }}" {% if topic in default_selected_topics %}checked{% endif %}> {{ topic }}
 </label>
 {% endfor %}
 </div>
 <div class="main-content">
 <div class="map-area" id="map-container"></div>
 <div class="info-panel">
 <h3>政策法规信息详情</h3>
 <div id="policy-info" class="empty-info">请点击地图中的国家查看相关政策法规信息</div>
 </div>
 </div>
 </div>
 <script>
 const df = {{ df_risk.to_json(orient='records') | safe }};
 const policyData = {{ policy_json | safe }};
 const topics = {{ esg_topics | tojson }};
 const sectors = {{ gics_sectors | tojson }};

 function renderMaps(sector, selectedTopics) {
 const container = document.getElementById('map-container');
 container.innerHTML = '';
 if (selectedTopics.length === 0) {
 container.innerHTML = '<div class="empty-message">请选择至少一个 ESG 议题</div>';
 return;
 }
 selectedTopics.forEach(topic => {
 const filtered = df.filter(row => row.Topic === topic && row.Sector === sector );
 if (filtered.length === 0) return;
 const trace = {
 type: 'choropleth',
 locations: filtered.map(r => r.Country_EN),
 z: filtered.map(r => r.Risk),
 text: filtered.map(r => `${r.Country_ZH}<br>风险值: ${r.Risk === -1 ? 'unknown' : r.Risk}`),
 hoverinfo: 'text',
 colorscale: [[0,'white'], [1,'darkred']],
 zmin: 0, zmax: 10,
 showscale: true,
 colorbar: { title: '风险值', len: 0.8, thickness: 20, yanchor: 'middle' },
 locationmode: 'country names',
 customdata: filtered.map(r => ({ country_zh: r.Country_ZH || r.Country_EN, topic: r.Topic, sector: r.Sector, risk: r.Risk }))
 };
 const layout = {
 title: topic,
 geo: { projection: { type: 'natural earth' }, showcoastlines: true, coastlinecolor: 'black', coastlinewidth: 0.5, landcolor: '#f9f9f9', oceancolor: 'white' },
 margin: { t: 50, b: 40, l: 40, r: 40 },
 paper_bgcolor: 'white',
 plot_bgcolor: 'white'
 };
 const divId = 'map-' + topic.replace(/[^a-zA-Z0-9]/g, '_');
 const div = document.createElement('div');
 div.id = divId;
 div.className = 'map-container';
 container.appendChild(div);
 Plotly.newPlot(divId, [trace], layout, { responsive: true });
 document.getElementById(divId).on('plotly_click', function(data) {
 if (data.points.length > 0) {
 const point = data.points[0];
 const country_zh = point.customdata.country_zh;
 const topic = point.customdata.topic;
 const sector = point.customdata.sector;
 const risk = point.customdata.risk;
 showPolicyInfo(country_zh, topic, sector, risk);
 }
 });
 });
 }

 function showPolicyInfo(country, topic, sector, risk) {
 const infoDiv = document.getElementById('policy-info');
 const key = country + '|' + topic + '|' + sector;
 const policies = policyData[key] || [];
 let html = '';
 html += `<div class="info-item"><span class="info-label">ESG 议题：</span><span class="info-value">${topic}</span></div>`;
 html += `<div class="info-item"><span class="info-label">所属行业：</span><span class="info-value">${sector}</span></div>`;
 html += `<div class="info-item"><span class="info-label">国家/地区：</span><span class="info-value">${country}</span></div>`;
 html += `<div class="info-item"><span class="info-label">ESG 风险值：</span><span class="info-value">${risk === -1 ? 'unknown' : risk.toFixed(1)}</span></div>`;
 html += `<hr style="margin: 15px 0; border: 0; border-top: 1px solid #eee;">`;
 if (policies.length === 0) {
 html += '<div class="empty-info">该国家在此议题下暂无相关政策法规信息</div>';
 infoDiv.innerHTML = html;
 return;
 }
 policies.forEach((p, idx) => {
 if (policies.length > 1) {
 html += `<div class="info-item"><span class="info-label">【${idx + 1}】政策名称：</span><span class="info-value">${p["政策法规名称"] || '—'}</span></div>`;
 } else {
 html += `<div class="info-item"><span class="info-label">政策法规名称：</span><span class="info-value">${p["政策法规名称"] || '—'}</span></div>`;
 }
 html += `<div class="info-item"><span class="info-label">生效时间：</span><span class="info-value">${p["生效时间"] || '—'}</span></div>`;
 html += `<div class="info-item"><span class="info-label">执行时间：</span><span class="info-value">${p["执行时间"] || '—'}</span></div>`;
 html += `<div class="info-item"><span class="info-label">主要规定：</span><br><span class="info-value">${p["主要规定"] || '—'}</span></div>`;
 html += `<div class="info-item"><span class="info-label">适用范围：</span><br><span class="info-value">${p["适用范围"] || '—'}</span></div>`;
 html += `<div class="info-item"><span class="info-label">对中国企业影响：</span><br><span class="info-value">${p["对中国企业的影响"] || '—'}</span></div>`;
 if (idx < policies.length - 1) {
 html += '<hr style="margin: 20px 0; border: 0; border-top: 1px dashed #eee;">';
 }
 });
 infoDiv.innerHTML = html;
 }

 document.addEventListener('DOMContentLoaded', () => {
 const sectorSel = document.getElementById('sector-select');
 const checkboxes = document.querySelectorAll('.topic-checkbox');

 function update() {
 const sector = sectorSel.value;
 const topics = Array.from(checkboxes)
 .filter(cb => cb.checked)
 .map(cb => cb.value);
 renderMaps(sector, topics);
 }

 document.getElementById('select-all-topics').addEventListener('change', function() {
 checkboxes.forEach(cb => cb.checked = this.checked);
 update();
 });

 sectorSel.addEventListener('change', update);
 checkboxes.forEach(cb => cb.addEventListener('change', update));
 update();
 });
 </script>
</body>
</html>'''

    # === 8. 渲染并保存 HTML ===
    output_file = "templates/global_esg_risk_map.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(Template(html_template_str).render(
            esg_topics=esg_topics,
            gics_sectors=gics_sectors,
            df_risk=df_risk,
            default_selected_topics=default_selected_topics,
            policy_json=policy_json_str
        ))

    print(f"\n✅ 已生成最终版 ESG 风险地图：{os.path.abspath(output_file)}")

if __name__ == "__main__":
    main()
