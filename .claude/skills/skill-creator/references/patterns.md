# Skill Patterns and Workflow Designs

## Choosing Your Approach: Problem-First vs Tool-First

- **Problem-first:** "I need to set up a project workspace" → skill orchestrates the right calls in the right sequence. Users describe outcomes; the skill handles tools.
- **Tool-first:** "I have Notion MCP connected" → skill teaches Claude optimal workflows and best practices. Users have access; skill provides expertise.

## Three Use Case Categories

### Category 1: Document and Asset Creation
Creating consistent, high-quality output — documents, code, designs, reports.

Key techniques:
- Embedded style guides and brand standards
- Template structures for consistent output
- Quality checklists before finalizing
- No external tools required — uses Claude's built-in capabilities

Example description:
> "Create distinctive, production-grade frontend interfaces with high design quality. Use when building web components, pages, artifacts, posters, or applications."

### Category 2: Workflow Automation
Multi-step processes that benefit from consistent methodology.

Key techniques:
- Step-by-step workflow with validation gates
- Templates for common structures
- Built-in review and improvement suggestions
- Iterative refinement loops

Example description:
> "Interactive guide for creating new skills. Walks through use case definition, frontmatter generation, instruction writing, and validation."

### Category 3: MCP Enhancement
Workflow guidance to enhance the tool access an MCP server provides.

Key techniques:
- Coordinates multiple MCP calls in sequence
- Embeds domain expertise
- Provides context users would otherwise need to specify
- Error handling for common MCP issues

Example description:
> "Automatically analyzes and fixes detected bugs in GitHub Pull Requests using Sentry's error monitoring data via their MCP server."

---

## Pattern 1: Sequential Workflow Orchestration

Use when: Users need multi-step processes in a specific order.

```markdown
## Workflow: Onboard New Customer

### Step 1: Create Account
Call MCP tool: `create_customer`
Parameters: name, email, company

### Step 2: Setup Payment
Call MCP tool: `setup_payment_method`
Wait for: payment method verification

### Step 3: Create Subscription
Call MCP tool: `create_subscription`
Parameters: plan_id, customer_id (from Step 1)

### Step 4: Send Welcome Email
Call MCP tool: `send_email`
Template: welcome_email_template
```

Key techniques:
- Explicit step ordering
- Dependencies between steps called out
- Validation at each stage
- Rollback instructions for failures

---

## Pattern 2: Multi-MCP Coordination

Use when: Workflows span multiple services.

```markdown
### Phase 1: Design Export (Figma MCP)
1. Export design assets from Figma
2. Generate design specifications
3. Create asset manifest

### Phase 2: Asset Storage (Drive MCP)
1. Create project folder in Drive
2. Upload all assets
3. Generate shareable links

### Phase 3: Task Creation (Linear MCP)
1. Create development tasks
2. Attach asset links to tasks

### Phase 4: Notification (Slack MCP)
1. Post handoff summary to #engineering
2. Include asset links and task references
```

Key techniques:
- Clear phase separation
- Data passing between MCPs documented
- Validation before moving to next phase

---

## Pattern 3: Iterative Refinement

Use when: Output quality improves with iteration.

```markdown
## Iterative Report Creation

### Initial Draft
1. Fetch data via MCP
2. Generate first draft report

### Quality Check
1. Run validation script: `scripts/check_report.py`
2. Identify issues: missing sections, formatting errors, data validation errors

### Refinement Loop
1. Address each identified issue
2. Regenerate affected sections
3. Re-validate
4. Repeat until quality threshold met

### Finalization
1. Apply final formatting
2. Save final version
```

---

## Pattern 4: Context-Aware Tool Selection

Use when: Same outcome, different tools depending on context.

```markdown
## Smart File Storage

### Decision Tree
1. Check file type and size
2. Determine best storage:
   - Large files (>10MB): Use cloud storage MCP
   - Collaborative docs: Use Notion/Docs MCP
   - Code files: Use GitHub MCP
   - Temporary files: Use local storage

### Execute Storage
Based on decision:
- Call appropriate MCP tool
- Apply service-specific metadata
- Explain to user why that storage was chosen
```

---

## Pattern 5: Domain-Specific Intelligence

Use when: Skill adds specialized knowledge beyond tool access.

```markdown
## Payment Processing with Compliance

### Before Processing (Compliance Check)
1. Fetch transaction details via MCP
2. Apply compliance rules:
   - Check sanctions lists
   - Verify jurisdiction allowances
   - Assess risk level
3. Document compliance decision

### Processing
IF compliance passed:
- Call payment processing MCP tool
- Apply appropriate fraud checks
ELSE:
- Flag for review
- Create compliance case

### Audit Trail
- Log all compliance checks
- Record processing decisions
```

---

## How MCP + Skills Work Together

| MCP (Connectivity) | Skills (Knowledge) |
|---|---|
| Connects Claude to your service | Teaches Claude how to use your service effectively |
| Provides real-time data access | Captures workflows and best practices |
| What Claude can do | How Claude should do it |

**Without skills:** Users connect MCP but don't know what to do. Each conversation starts from scratch. Inconsistent results because users prompt differently each time.

**With skills:** Pre-built workflows activate automatically. Consistent, reliable tool usage. Best practices embedded in every interaction.
