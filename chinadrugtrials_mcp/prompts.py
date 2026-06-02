"""Prompt definitions for chinadrugtrials.org.cn MCP server.

Provides LLM-guided analysis prompts, following the clinicaltrialsgov-mcp-server
pattern of `analyze_trial_landscape`.
"""


async def analyze_china_trial_landscape(topic: str, focus_areas: str = "") -> str:
    """Generate a prompt for analyzing the China clinical trial landscape.

    Guides structured analysis of registered trials on chinadrugtrials.org.cn
    for a specific topic (drug, disease, or therapeutic area).

    Args:
        topic: The therapeutic area, drug class, or indication to analyze
               (e.g., "PD-1 inhibitors", "非小细胞肺癌", "COVID-19 vaccine")
        focus_areas: Optional comma-separated list of focus dimensions
                      (e.g., "phase_distribution,sponsor_landscape,enrollment_status")

    Returns:
        str: A structured prompt for the LLM to perform landscape analysis.
    """
    prompt_lines = [
        f"# 中国临床试验格局分析: {topic}",
        "",
        f"请基于中国药物临床试验登记与信息公示平台 (chinadrugtrials.org.cn) 的数据，对 **{topic}** 领域的临床试验格局进行系统分析。",
        "",
        "## 分析任务",
        "",
        "1. **搜索并汇总**该领域的所有已登记临床试验",
        "2. **分析试验分布**：按药物类型（中药/化学药物/生物制品）、分期（I/II/III/IV期）、状态进行统计",
        "3. **申办方分析**：识别主要申办企业和研究机构",
        "4. **适应症覆盖**：梳理试验覆盖的适应症范围",
        "5. **入组状态**：评估试验进展（招募中/已完成/暂停等）",
        "",
    ]

    if focus_areas:
        prompt_lines.append(f"## 重点关注维度: {focus_areas}")
        prompt_lines.append("")

    prompt_lines.extend([
        "## 输出要求",
        "",
        "- 使用中文输出",
        "- 包含具体数据和数字",
        "- 提供趋势洞察和竞争格局分析",
        "- 标注数据来源和时间范围",
        "",
        "请调用 `chinadrugtrials_search_trials` 工具搜索相关试验数据，然后进行分析。",
    ])

    return "\n".join(prompt_lines)
