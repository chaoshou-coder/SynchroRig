# 技术详解 (Technical Details)

本模板的核心是利用Cursor原生Subagents、Skills、Rules实现Planner-Implementers-Verifier闭环。以下按模块拆解已敲定部分与仍待验证/完善的部分。

## 1. Rules (.cursor/rules/)

**现状**：已落地（以 `.mdc` + frontmatter 的 Project Rules 形式提供）

**已敲定原则**：
- 强制PR粒度（100-300 LOC，≤10文件，单一意图、可独立验证）。
- 强制Spec-First TDD（先写红测试→验证失败→实现变绿）。
- 关键信息外置到PROGRESS.md。

**待开发ToDoList**（独立文件：doc/rules_todo.md）：
- 编写granularity：完整prompt约束粒度量化与风险分类标准。（已完成：`granularity.mdc`）
- 编写tdd：完整prompt强制红/绿验证流程与外部化规则。（已完成：`tdd.mdc`）
- 编写memory：定义PROGRESS.md/SUMMARY.md写入格式模板（必填字段：决策、接口、进度、证据）。（已完成：`memory.mdc`）
- 测试Rules加载后是否在所有subagent中生效。

## 2. Subagents (.cursor/agents/)

### 2.1 Planner Subagent (planner.md)

**现状**：已提供可用 prompt（strict JSON 输出 + 粒度/风险/并行数约束）

**已敲定配置**：
- 模型：GPT-5.2（非codex变体）。

**已敲定职责**：
- 负责hierarchical decomposition到PR粒度。
- 风险评估（低/中/高）。
- 动态路由parallel N（低:1，中:2，高:3-5）。

**待开发ToDoList**（独立文件：doc/planner_todo.md）：
- 编写完整prompt（包含：输入需求→输出JSON任务树格式、风险分类逻辑、动态N决策规则、sub-tasking触发条件）。
- 定义输出结构标准（任务ID、描述、风险级别、parallel_count）。
- 在小需求上验证分解粒度稳定性（目标：平均150-250 LOC/任务）。

### 2.2 Implementers Subagent (implementers.md)

**现状**：已提供可用 prompt（Spec-First TDD + 必跑 make test/check + 并行候选标注）

**已敲定配置**：
- 模型：GPT-5.2 codex extra high。
- 并行数：动态（由Planner路由）。
- 强制Spec-First：先写红测试→自行run make test验证失败→实现变绿。

**待开发ToDoList**（独立文件：doc/implementers_todo.md）：
- 编写完整prompt（包含：接收Planner任务→先写pytest红测试→run make test验证红→实现代码→run make test验证绿→输出最终代码+测试日志）。
- 定义并行协调机制（多实现时标注版本1/2/3）。
- 测试并行生成质量（目标：至少2/3实现可通过初步check）。

### 2.3 Verifier Subagent (verifier.md)

**现状**：已提供可用 prompt（机器证据验收 + judging 选优 + 写入 PROGRESS）

**已敲定配置**：
- 模型：Claude Opus 4.5。
- 职责：invoke verification skill→解析make check输出→judging选优→grind until "All checks passed!"→失败时触发sub-tasking。

**待开发ToDoList**（独立文件：doc/verifier_todo.md）：
- 编写完整prompt（包含：接收Implementers多实现→run verification skill→解析机器输出→judging标准（正确性>简洁>性能）→选优报告证据→失败时生成sub-tasking请求格式）。
- 定义grind循环逻辑（最大迭代次数、早停条件）。
- 测试judging准确率（目标：选出最佳实现≥90%）。

## 3. Skills (.cursor/skills/)

### 3.1 Verification Skill (verification/SKILL.md + scripts/)

**现状**：已落地（Windows: `run-check.ps1`，Linux/Mac: `run-check.sh`，并更新 SKILL.md）

**已敲定职责**：
- 执行make check获取机器反馈。
- 解析红/绿状态。

**待开发ToDoList**（独立文件：doc/skills_todo.md）：
- （可选）返回结构化JSON（ps1 支持 `-Json`；sh 未实现）。
- 在 CI/不同环境下验证回退路径可靠性（例如无 `make` 时）。

## 4. 示例基础设施

### 4.1 Makefile（已敲定，完全可直接复制）

```makefile
.PHONY: check format test clean

# 1. 格式化与自动修复 (让机器先修掉低级错误)
format:
	@echo "Formatting..."
	ruff format .
	ruff check . --fix

# 2. 静态检查 (只报硬伤，不报风格建议)
lint:
	@echo "Linting..."
	ruff check .

# 3. 运行测试 (关键验收步骤)
test:
	@echo "Running tests..."
	pytest -vv --tb=short tests/

# 4. 一键验收 (Agent 的最终目标)
check: format lint test
	@echo "All checks passed!"


```

说明：Agent只需运行make check即可获得完整机器反馈，Verifier skill解析最终"All checks passed!"作为pass信号。


### 4.2 tests/ 与 PROGRESS.md
现状：已提供最小可跑通示例（`tests/` + `Makefile`），并提供 `PROGRESS.md` 模板与大任务初始化脚本。
待开发ToDoList（合并到doc/rules_todo.md）：

创建最小demo测试文件（至少1个红/绿示例）。
定义PROGRESS.md模板（Markdown表格：任务ID | 描述 | 状态 | 关键决策 | 接口契约 | 验证证据）。（已完成并对齐初始化脚本）


## 5. 仓库与发布

- 项目名：**SynchroRig**（Cursor 工作流模板，Spec-First TDD + Planner-Implementers-Verifier）。
- 不提交内容（见 `.gitignore`）：`.cursor/`、`runs/`、`x.com/`、`REPORT.md` 及 Python/工具缓存。
- 用户克隆后：复制 `template-cursor/` 为 `.cursor/` 即可使用；`make check` 验证示例链路。


