"""
Search History Cases Skill — 数据模型
所有输入/输出的 Pydantic 模型及常量定义。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# ── 工作制枚举映射（仅非航修任务填写）─────────────────────────
WORK_SCHEDULE_MAP: dict[int, str] = {
    1: "8小时/日",
    2: "9小时/日",
    3: "10小时/日",
    4: "11小时/日",
    5: "12小时/日",
    6: "24小时/日",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 输入模型
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class RequirementInput(BaseModel):
    """服务需求单检索侧字段，由上层 Agent 或命令行参数构造。"""

    # 必填
    business_type: str = Field(
        description="业务归口，枚举值：电气 / 轮机",
        examples=["轮机", "电气"],
    )
    service_desc_code: str = Field(
        description="服务描述编码，如 RS0000000001",
    )

    # 次检索维度（可 NULL）
    service_type_code: Optional[str] = Field(
        default=None,
        description="服务类型编码，如 CS0006。允许 NULL，约 95% 有值",
    )

    # 设备维度（可 NULL，有则精确加权）
    equipment_model_code: Optional[str] = Field(
        default=None,
        description="新设备型号编码，如 ET000000000005",
    )

    # 文本排序辅助（可 NULL）
    task_description: Optional[str] = Field(
        default=None,
        description="施工任务描述，用于 pg_trgm 模糊排序",
    )

    # 备注（可 NULL，仅用于相似度补充标注，不影响排序）
    remark: Optional[str] = Field(
        default=None,
        description="备注文本，填写率 ~50%。不影响排序，仅附加匹配说明",
    )

    # 上层 Agent 动态配置
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="返回案例数，默认 5，上层 Agent 可动态传入，最大 20",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 输出模型
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PersonnelItem(BaseModel):
    """人员工时明细条目（来自 evaluation_personnel 子表）"""
    work_type_code: Optional[str] = None
    work_type_name: Optional[str] = None
    job_level_code: Optional[str] = None
    job_level_name: Optional[str] = None
    quantity: Optional[int] = None
    construction_hour: Optional[float] = None
    task_desc: Optional[str] = Field(
        default=None,
        description="详细工作内容（任务分组键），NULL 表示历史数据未填写",
    )


class EquipmentInfo(BaseModel):
    """设备信息摘要"""
    model_code: Optional[str] = None
    model_name: Optional[str] = None
    qty: Optional[int] = None
    unit: Optional[str] = None


class ToolItem(BaseModel):
    """需求工具条目（toolTypeNo 有值，无 model 字段）"""
    tool_name: str
    tool_type_no: Optional[int] = None
    quantity: int
    unit_code: Optional[str] = None
    unit_name: Optional[str] = None


class MaterialItem(BaseModel):
    """耗材条目（含 model 型号，toolTypeNo 为 null）"""
    tool_name: str
    model: Optional[str] = Field(default=None, description="耗材型号")
    quantity: int
    unit_code: Optional[str] = None
    unit_name: Optional[str] = None


class SpecialToolItem(BaseModel):
    """专用工具条目（结构与耗材相同，含 model 型号）"""
    tool_name: str
    model: Optional[str] = Field(default=None, description="专用工具型号")
    quantity: int
    unit_code: Optional[str] = None
    unit_name: Optional[str] = None


class HistoryCaseResult(BaseModel):
    """单条历史案例检索结果"""

    case_id: str = Field(description="服务单号，如 RH-2025-0009611001")
    match_reason: str = Field(
        description="匹配依据说明；条件放宽时追加 '⚠️ 服务类型条件已放宽'"
    )
    task_sim_score: float = Field(description="任务描述 pg_trgm 相似度，0~1")
    remark_sim_score: Optional[float] = Field(
        default=None,
        description="备注相似度（仅输入有备注时计算）",
    )
    evaluated_at: Optional[datetime] = None
    equipment_info: EquipmentInfo

    risk_description: Optional[str] = None
    task_description: Optional[str] = None

    total_persons: Optional[int] = Field(
        default=None, description="综述总人数，填写率 ~80%"
    )
    total_days: Optional[float] = Field(
        default=None, description="综述总天数，填写率 ~80%"
    )
    work_schedule: Optional[int] = Field(
        default=None, description="工作制枚举值 1~6，仅非航修任务填写"
    )
    work_schedule_label: Optional[str] = Field(
        default=None, description="工作制可读标签，如 '12小时/日'"
    )
    construction_hours: Optional[float] = None
    inspection_hours: Optional[float] = None

    personnel: list[PersonnelItem] = Field(default_factory=list)
    tools: list[ToolItem] = Field(default_factory=list)
    materials: list[MaterialItem] = Field(default_factory=list)
    special_tools: list[SpecialToolItem] = Field(default_factory=list)


class SearchOutput(BaseModel):
    """SearchHistoryCasesSkill 完整输出"""

    cases: list[HistoryCaseResult]
    total_found: int = Field(description="精确粗筛的候选集总数")
    relaxed: bool = Field(description="是否触发了条件放宽")
    input_echo: RequirementInput = Field(description="回显输入参数，便于调试")