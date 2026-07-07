# Product Requirements Document (PRD)

**Title:** AI-Powered Discount Strategy Suggestion Agent  
**Date:** 2026-07-06  
**Owner:** Sales Operations  
**Solution Category:** AI Agent

## Product Purpose & Value Proposition

**Elevator Pitch:**  
Sales reps negotiate discounts in the dark — relying on gut feel while margin targets sit locked in SAP. This agent reads live order data and pricing conditions from S/4HANA SD, reasons over margin constraints using AI, and delivers ranked, context-aware discount recommendations directly to the rep before they commit to a price.

**Business Need:**  
Inconsistent discounting leads to margin erosion and lost deals. Sales reps lack real-time visibility into how a proposed discount affects profitability. There is no standard SAP capability that combines order context, pricing conditions, and AI reasoning into an actionable recommendation.

**Expected Value:**  
Reduced margin leakage from unguided discounting; faster, more confident deal negotiation; consistent discount governance across the sales team.

**Product Objectives:**
1. Provide margin-safe discount recommendations grounded in live S/4HANA data for every sales inquiry.
2. Enable reps to simulate discount impact before committing to a price.
3. Deliver recommendations in natural language, requiring no SAP transaction expertise.

## Requirements

### Must-Have Requirements

**R1: Customer Order Context Retrieval**
- **User Story**: As a sales rep, I need the agent to pull the customer's current order and history from S/4HANA so that recommendations are based on real data, not estimates.
- **Acceptance Criteria**: Given a customer and order identifier, the agent retrieves order lines, quantities, and pricing from the Sales Order API within 5 seconds.
- **Priority Rank**: 1

**R2: Margin Impact Simulation**
- **User Story**: As a sales rep, I need the agent to simulate how a candidate discount affects the order margin so that I can see the financial impact before agreeing.
- **Acceptance Criteria**: Given a discount percentage, the agent calls the Sales Order Simulation API and returns the resulting margin, net price, and delta vs. the margin target.
- **Priority Rank**: 2

**R3: Ranked Discount Recommendations**
- **User Story**: As a sales rep, I need the agent to suggest 2-3 discount options ranked by margin safety so that I can choose the best trade-off between deal competitiveness and profitability.
- **Acceptance Criteria**: Agent returns at least two distinct discount options; each option includes discount %, resulting margin %, and a plain-language rationale. No option breaches the configured margin floor.
- **Priority Rank**: 3

**R4: Margin Floor Guardrail**
- **User Story**: As a sales manager, I need the agent to enforce a configurable minimum margin threshold so that reps cannot receive recommendations that destroy profitability.
- **Acceptance Criteria**: Agent refuses to recommend any discount that would push margin below the configured floor; it explains why and offers the closest compliant option.
- **Priority Rank**: 4

**R5: Conversational Delivery**
- **User Story**: As a sales rep, I need recommendations delivered in plain language through a chat interface so that I don't need SAP transaction knowledge to act on them.
- **Acceptance Criteria**: Agent responds in a single conversational message with structured options clearly labelled; no raw API data is exposed to the user.
- **Priority Rank**: 5

## Solution Architecture

**Architecture Overview:**  
A Python-based AI agent deployed on SAP BTP, implementing the A2A protocol. The agent exposes a conversational interface and orchestrates multiple S/4HANA SD OData API calls. An LLM hosted on SAP AI Core performs the reasoning and recommendation generation.

**Key Components:**
- AI Agent runtime (Python, A2A protocol) on SAP BTP — orchestrates tool calls and LLM reasoning
- SAP AI Core (LLM) — generates natural language recommendations from structured pricing data
- SAP S/4HANA SD OData APIs — data source for orders, prices, conditions, and simulation
- MCP tool wrappers — expose S/4HANA APIs as callable agent tools

**Integration Points:**
- `API_SALES_ORDER_SRV:v1` — read customer sales order header and item data
- `API_SLSPRICINGCONDITIONRECORD_SRV:v1` — read active discount and pricing conditions
- `SALESPRICE_0001:v1` — retrieve current list prices per customer/material
- `API_SALES_ORDER_SIMULATION_SRV:v1` — simulate margin impact of candidate discounts
- `API_SLSPRICINGCONDITIONTYPE_SRV:v1` — read discount condition type definitions

### Agent Extensibility & Instrumentation

**Agent Extensibility:**
- The agent is designed with pluggable tool wrappers so additional S/4HANA APIs (e.g., Sales Quotation, Billing) can be added without changing the core reasoning loop.
- A configurable margin floor parameter allows sales managers to set thresholds per sales organisation without code changes.
- The recommendation engine prompt is externalised to allow business-driven tuning of discount strategy logic.

**Business Step Instrumentation:**
- All five key milestones (see below) must emit structured log entries on achievement and on miss.
- Log pattern: `[MILESTONE_ID].[achieved|missed]: [description]`
- Logs are forwarded to SAP BTP observability tooling for monitoring and alerting.

### Automation & Agent Behaviour

**Automation Level:** Autonomous agent (read + simulate only; no write to SAP without rep confirmation)

**Actions performed without human approval:**
- Retrieve sales order data from S/4HANA
- Retrieve pricing conditions and list prices
- Run order simulation scenarios
- Generate and rank discount recommendations

**Actions requiring human review:**
- Applying any discount to an actual sales order (rep must confirm)
- Overriding the margin floor (sales manager approval required)

**Model:** SAP Generative AI Hub (GPT-4o or equivalent) via SAP AI Core

**Knowledge & data sources:**
- SAP S/4HANA SD: sales orders, pricing conditions, list prices, simulation results
- Configurable margin floor: set per sales organisation by the sales manager

**Tools invoked:**
- `get_sales_order` — read order data (read-only)
- `get_pricing_conditions` — read discount conditions (read-only)
- `get_list_price` — retrieve current list price (read-only)
- `simulate_order_discount` — run pricing simulation (read-only)
- `get_condition_types` — read condition type config (read-only)

**Guardrails & fail-safes:**
- Agent never writes to SAP; all recommendations are advisory only.
- Margin floor is enforced before any option is surfaced; breaching options are suppressed.
- If S/4HANA API returns an error, agent informs the rep and declines to recommend.
- If LLM confidence is low, agent flags the recommendation as indicative and suggests manager review.

## Milestones

### M1: Order Context Retrieved
- **Description**: Agent has successfully fetched the customer's current order and relevant history from S/4HANA SD.
- **Achieved when**: Sales Order API returns valid order data for the given customer/order ID.
- **Log on achievement**: `M1.achieved: customer order context retrieved for order {order_id}`
- **Log on miss**: `M1.missed: failed to retrieve order context for order {order_id} — {error}`

### M2: Margin Targets Evaluated
- **Description**: Agent has retrieved pricing conditions and identified the applicable margin floor for the customer/sales org.
- **Achieved when**: Pricing conditions and margin floor configuration are loaded without error.
- **Log on achievement**: `M2.achieved: margin targets evaluated — floor={margin_floor}% for sales_org={sales_org}`
- **Log on miss**: `M2.missed: margin target evaluation failed — {error}`

### M3: Discount Recommendation Generated
- **Description**: Agent has produced at least two ranked discount options that comply with the margin floor.
- **Achieved when**: LLM returns a structured recommendation with ≥2 compliant options.
- **Log on achievement**: `M3.achieved: {n} discount options generated for order {order_id}`
- **Log on miss**: `M3.missed: no compliant discount options could be generated — margin_floor={margin_floor}%`

### M4: Recommendation Delivered to Sales Rep
- **Description**: Agent has presented the recommendations to the sales rep in a conversational response.
- **Achieved when**: Agent response is sent to the rep's chat interface without error.
- **Log on achievement**: `M4.achieved: recommendation delivered to rep {rep_id} for order {order_id}`
- **Log on miss**: `M4.missed: delivery failed for rep {rep_id} — {error}`

### M5: Feedback Captured
- **Description**: Sales rep has accepted, rejected, or modified the recommendation; outcome is recorded.
- **Achieved when**: Rep's response (accept/reject/modify) is logged with the corresponding order and recommendation ID.
- **Log on achievement**: `M5.achieved: rep feedback captured — outcome={outcome} for order {order_id}`
- **Log on miss**: `M5.missed: no feedback received within timeout for order {order_id}`
