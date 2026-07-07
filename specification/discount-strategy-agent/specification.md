# Specification: discount-strategy-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [ ] Read the project input (`product-requirements-document.md`, `intent.md`)
- [ ] Bootstrap agent code in `assets/discount-strategy-agent/` using skill `sap-agent-bootstrap` (invoke from inside `assets/discount-strategy-agent/`, use copy commands — do NOT create files manually)
- [ ] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

## API Spec Download

> The pre-signed download URLs expired during spec generation. Re-discover and download specs at execution time.

- [ ] Call `sap_knowledge_graph_api_discovery` with query `"SAP S/4HANA Sales Order pricing conditions simulation discount SD"` to retrieve fresh download URLs
- [ ] Download the EDMX spec for **Sales Order (A2X)** (`sap.s4:apiResource:API_SALES_ORDER_SRV:v1`) → save as `specification/discount-strategy-agent/api-specs/sales-order.edmx`
- [ ] Download the EDMX spec for **Condition Record for Pricing in Sales** (`sap.s4:apiResource:API_SLSPRICINGCONDITIONRECORD_SRV:v1`) → save as `specification/discount-strategy-agent/api-specs/pricing-conditions.edmx`
- [ ] Download the EDMX spec for **Sales Order - Simulate (A2X)** (`sap.s4:apiResource:API_SALES_ORDER_SIMULATION_SRV:v1`) → save as `specification/discount-strategy-agent/api-specs/sales-order-simulation.edmx`
- [ ] Download the EDMX spec for **Sales Price - Retrieve (A2X)** (`sap.s4:apiResource:SALESPRICE_0001:v1`) → save as `specification/discount-strategy-agent/api-specs/sales-price.edmx`
- [ ] Download the EDMX spec for **Condition Type for Pricing in Sales – Read** (`sap.s4:apiResource:API_SLSPRICINGCONDITIONTYPE_SRV:v1`) → save as `specification/discount-strategy-agent/api-specs/pricing-condition-types.edmx`

## MCP Translation & Server Setup

- [ ] Invoke `mcp-translation-file` skill for each downloaded EDMX spec file in `specification/discount-strategy-agent/api-specs/` — pass file path, `apiType: "edmx"`, and the corresponding ORD ID:
  - `sales-order.edmx` → ORD ID `sap.s4:apiResource:API_SALES_ORDER_SRV:v1`
  - `pricing-conditions.edmx` → ORD ID `sap.s4:apiResource:API_SLSPRICINGCONDITIONRECORD_SRV:v1`
  - `sales-order-simulation.edmx` → ORD ID `sap.s4:apiResource:API_SALES_ORDER_SIMULATION_SRV:v1`
  - `sales-price.edmx` → ORD ID `sap.s4:apiResource:SALESPRICE_0001:v1`
  - `pricing-condition-types.edmx` → ORD ID `sap.s4:apiResource:API_SLSPRICINGCONDITIONTYPE_SRV:v1`
  - **If `mcp-translation-file` skill is unavailable**, skip this section and log: `[MCP-SKILL] mcp-translation-file unavailable — skipping MCP server asset generation.`
- [ ] Invoke `setup-solution` skill to register all generated MCP server assets in `solution.yaml`

## Project-Specific Agent Tasks

### Agent Identity & System Prompt

- [ ] In `app/agent.py`, set the agent name to `"Discount Strategy Agent"` and description to `"Analyzes SAP S/4HANA customer orders and margin targets to provide sales reps with ranked, margin-safe discount recommendations."`
- [ ] In `@prompt_section`, write the system prompt:
  - Instruct the agent to only provide discount recommendations grounded in live S/4HANA data — never hallucinate order data, prices, or margin figures.
  - Instruct the agent to enforce the configured margin floor (`MARGIN_FLOOR_PCT` env var, default 20%) — never recommend a discount that pushes margin below this threshold.
  - Instruct the agent to always set `top` (or equivalent page-size) to a maximum of 100 on every tool call that accepts it.
  - Instruct the agent to present 2-3 ranked discount options with a plain-language rationale for each.
  - Instruct the agent to inform the user that all recommendations are advisory — no changes are made to SAP without explicit rep confirmation.
- [ ] Define a Python constant `DEFAULT_MARGIN_FLOOR_PCT = float(os.getenv("MARGIN_FLOOR_PCT", "20.0"))` at module level

### Runtime Skill: Discount Strategy Logic

- [ ] Create `app/skills/discount-strategy/SKILL.md` with frontmatter (`name: discount-strategy`, `description: Step-by-step instructions for the agent to retrieve order context, evaluate margin, and generate ranked discount recommendations`) and the following body:
  - Step 1: Retrieve the customer's sales order using the `get_sales_order` tool; extract order lines, quantities, and net prices.
  - Step 2: Retrieve active pricing conditions for the customer/material using the `get_pricing_conditions` tool; identify applicable discount condition types.
  - Step 3: Retrieve the current list price using the `get_list_price` tool.
  - Step 4: Propose 2-3 candidate discount percentages (e.g. 5%, 10%, 15%) and simulate each using the `simulate_order_discount` tool; capture resulting net margin for each.
  - Step 5: Filter out any option where simulated margin < `MARGIN_FLOOR_PCT`.
  - Step 6: Rank remaining options by margin health (highest margin first). If all options are filtered, return the closest compliant option with an explanation.
  - Step 7: Format output as a structured list with: discount %, resulting net price, resulting margin %, and a plain-language rationale. Append an advisory note that applying the discount requires rep confirmation in SAP.

### Agent Tools (MCP wrappers)

> All tools are exposed via MCP servers generated from the EDMX specs above. Wire them via `get_mcp_tools()` — never hard-code tool names.

- [ ] In `app/agent.py`, load tools lazily via `_get_tools()` using the canonical MCP pattern from `guidelines-agent.md`
- [ ] Confirm the agent graph resolves tools by capability (not by name) at runtime

### Business Step Instrumentation

Implement all five milestones from the PRD using the pattern `[MILESTONE_ID].[achieved|missed]: [description]`. Extract all business logic from `stream()` into `_run_agent()` and instrument that method with OpenTelemetry spans. Never wrap `yield` inside `with tracer.start_as_current_span(...)`.

- [ ] **M1 — Order Context Retrieved**
  - Log on achievement: `M1.achieved: customer order context retrieved for order {order_id}`
  - Log on miss: `M1.missed: failed to retrieve order context for order {order_id} — {error}`
  - OTel span: `"m1_order_context_retrieved"`
- [ ] **M2 — Margin Targets Evaluated**
  - Log on achievement: `M2.achieved: margin targets evaluated — floor={margin_floor}% for sales_org={sales_org}`
  - Log on miss: `M2.missed: margin target evaluation failed — {error}`
  - OTel span: `"m2_margin_targets_evaluated"`
- [ ] **M3 — Discount Recommendation Generated**
  - Log on achievement: `M3.achieved: {n} discount options generated for order {order_id}`
  - Log on miss: `M3.missed: no compliant discount options could be generated — margin_floor={margin_floor}%`
  - OTel span: `"m3_discount_recommendation_generated"`
- [ ] **M4 — Recommendation Delivered to Sales Rep**
  - Log on achievement: `M4.achieved: recommendation delivered to rep {rep_id} for order {order_id}`
  - Log on miss: `M4.missed: delivery failed for rep {rep_id} — {error}`
  - OTel span: `"m4_recommendation_delivered"`
- [ ] **M5 — Feedback Captured**
  - Log on achievement: `M5.achieved: rep feedback captured — outcome={outcome} for order {order_id}`
  - Log on miss: `M5.missed: no feedback received within timeout for order {order_id}`
  - OTel span: `"m5_feedback_captured"`
- [ ] Verify `auto_instrument()` is called at top of `main.py` before any AI framework imports

### asset.yaml Dependencies

- [ ] Add MCP server `requires` entries to `assets/discount-strategy-agent/asset.yaml` for each generated MCP server (one per API spec translated). Use the ORD IDs listed in the MCP Translation section above with `-MCP` suffix naming convention.

### Mock MCP Configuration

- [ ] Invoke `mcp-mock-config` skill to generate `mcp-mock.json` — run AFTER `mcp-translation-file` and `setup-solution` complete
  - If `mcp-translation-file` was skipped, skip this step too

### Cleanup

- [ ] Delete the template runtime skill: `rm -rf assets/discount-strategy-agent/app/skills/template-skill/`

## Testing

- [ ] `conftest.py` only sets `IBD_TESTING=true`
- [ ] Write unit test for `get_sales_order` tool wrapper — mock MCP response with sample order data; assert order_id, items, and net price are extracted correctly
- [ ] Write unit test for `get_pricing_conditions` tool — mock response with at least one discount condition record; assert condition type and rate are parsed
- [ ] Write unit test for `simulate_order_discount` tool — mock simulation response; assert margin calculation logic returns correct margin % for a 10% discount
- [ ] Write unit test for `get_list_price` tool — mock response; assert list price is returned correctly
- [ ] Write unit test for margin floor guardrail logic — verify that discount options below `DEFAULT_MARGIN_FLOOR_PCT` are filtered out and not surfaced to the rep
- [ ] Write one integration test: simulate a full agent conversation — rep asks for discount options on order "1000012345", mock all MCP tools and LLM, assert response contains at least two ranked options with margin % above the floor
- [ ] Run `pytest` from `assets/discount-strategy-agent/` (no args) — fix failures before proceeding
- [ ] If coverage < 70%, add targeted tests until threshold met
- [ ] Verify `grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/discount-strategy-agent/app/agent.py` returns exactly 3
- [ ] Run `pytest` again (no args) to generate final `test_report.json`
- [ ] Verify `test_report.json` exists in `assets/discount-strategy-agent/`

## Agent Evaluation

- [ ] Invoke `sap-aeval-generate-tool-schema` skill from `assets/discount-strategy-agent/` to produce `tools.json`
- [ ] Invoke `sap-aeval-generate-testcase` skill from `assets/discount-strategy-agent/` passing `specification/discount-strategy-agent/specification.md` and `tools.json` — review generated test cases and replace placeholder values with realistic S/4HANA order data before running evaluations
