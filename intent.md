# AI-Powered Discount Strategy Suggestion Agent

## Business challenge

Sales representatives lack real-time, data-driven guidance when negotiating discounts with customers. They manually assess order history and margin targets from SAP S/4HANA SD, leading to inconsistent discounting, margin erosion, and lost deals. An AI agent is needed to analyze live order and pricing data and deliver contextualized, margin-safe discount recommendations directly to sales reps.

## Key Milestones

1. **Order Context Retrieved** — Agent successfully fetches customer order history and current order details from SAP S/4HANA SD via API.
2. **Margin Targets Evaluated** — Agent retrieves pricing condition records and calculates the margin impact of candidate discounts against defined targets.
3. **Discount Recommendation Generated** — Agent produces a ranked set of discount options with justification, respecting margin floors.
4. **Recommendation Delivered to Sales Rep** — Agent presents recommendations in a conversational format suitable for the sales rep's workflow.
5. **Feedback Captured** — Sales rep accepts, rejects, or modifies the recommendation; outcome is logged for continuous improvement.

## Business Architecture (RBA)

### End-to-End Process

Lead to Cash

### Process Hierarchy

```
Lead to Cash
└── Order to Fulfill (generic)
    └── Manage customer orders and contracts (generic) [BPS-361]
        └── Manage customer orders
        └── Plan prices and promotions
```

### Summary

The challenge maps to the Lead to Cash E2E process, specifically the "Manage customer orders" and "Plan prices and promotions" activities in SAP S/4HANA SD, where AI-driven margin-aware discount recommendations augment existing pricing determination and order management capabilities.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | MCP Server Version | Gap? | Notes / assumptions |
| ---------------------- | ----------------------- | ---------- | ----------------- | ------------------ | ---- | ------------------- |
| Read customer sales orders | SAP S/4HANA Sales Order Management | `sap.s4:apiResource:API_SALES_ORDER_SRV:v1` | — | — | No | Standard OData API available; no MCP server found — API used directly |
| Read pricing condition records | SAP S/4HANA Sales Price Calculation | `sap.s4:apiResource:API_SLSPRICINGCONDITIONRECORD_SRV:v1` | — | — | No | Condition records (discounts, surcharges) readable via OData |
| Retrieve current sales prices | SAP S/4HANA Sales Price Planning | `sap.s4:apiResource:SALESPRICE_0001:v1` | — | — | No | Sales Price Retrieve API provides list prices per customer/material |
| Simulate order with discount applied | SAP S/4HANA Sales Order Simulation | `sap.s4:apiResource:API_SALES_ORDER_SIMULATION_SRV:v1` | — | — | No | Simulation API allows margin impact testing before committing |
| Retrieve pricing procedures and condition types | SAP S/4HANA Pricing Configuration | `sap.s4:apiResource:API_SLSPRICINGCONDITIONTYPE_SRV:v1` | — | — | No | Condition types define discount structure (%, amount, etc.) |
| AI reasoning over margin targets + order context | No standard SAP product | — | — | — | Yes | Requires custom AI agent using LLM with tool-calling to SAP APIs |
| Contextualized discount recommendation narrative | No standard SAP product | — | — | — | Yes | Custom AI agent must synthesize data and generate natural language output |

### Key findings
- SAP S/4HANA SD provides rich OData APIs for orders, pricing, and simulation — no MCP servers are currently available, so APIs will be wrapped as agent tools.
- The Sales Order Simulation API (`API_SALES_ORDER_SIMULATION_SRV`) is a critical differentiator — it enables the agent to test discount scenarios without creating actual orders.
- SAP S/4HANA covers Sales Price Calculation (SC5494/SC1036) and Sales Price Planning (SC5495/SC1044) natively; the gap lies solely in the AI reasoning and recommendation layer.
- A custom AI agent on SAP BTP (Python, A2A protocol) is the right fit to bridge the gap — it orchestrates multiple S/4HANA API calls, reasons over margin constraints, and generates recommendations.
- No existing SAP product provides AI-driven, context-aware discount advisory for sales reps; this is a custom development opportunity.

## Recommendations

### AI Discount Strategy Agent on SAP BTP

#### Executive Summary

Custom AI agent on BTP integrating S/4HANA SD APIs for real-time discount advisory.

#### Recommended Solution

Build a Python-based AI agent (A2A protocol) on SAP BTP that connects to SAP S/4HANA SD via OData APIs. The agent retrieves customer order history, current pricing, and margin targets, then uses an LLM (via SAP AI Core) to reason over the data and produce ranked, margin-safe discount recommendations delivered conversationally to sales reps.

#### Recommended solution category

AI Agent

#### Intent fit
88%
