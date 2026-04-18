# Evaluating Skill Output Quality

## Designing Test Cases

A test case has three parts:
- **Prompt**: realistic user message — what someone would actually type
- **Expected output**: human-readable description of what success looks like
- **Input files** (optional): files the skill needs

Store in `evals/evals.json` inside the skill directory:

```json
{
  "skill_name": "csv-analyzer",
  "evals": [
    {
      "id": 1,
      "prompt": "I have a CSV of monthly sales data in data/sales_2025.csv. Can you find the top 3 months by revenue and make a bar chart?",
      "expected_output": "A bar chart image showing the top 3 months by revenue, with labeled axes and values.",
      "files": ["evals/files/sales_2025.csv"]
    }
  ]
}
```

**Tips for good test prompts:**
- Start with 2-3 test cases. Don't over-invest before first results.
- Vary phrasing, detail level, and formality
- Cover at least one edge/boundary case
- Use realistic context (file paths, column names, personal context)

---

## Running Evals

Run each test case twice: **with the skill** and **without it** (baseline comparison).

Each run should start with clean context — no leftover state.

**Workspace structure:**
```
skill-workspace/
└── iteration-1/
    ├── eval-top-months-chart/
    │   ├── with_skill/
    │   │   ├── outputs/
    │   │   └── grading.json
    │   └── without_skill/
    │       ├── outputs/
    │       └── grading.json
    └── benchmark.json
```

---

## Writing Assertions

Assertions are verifiable statements about what the output should contain.

**Good assertions:**
- `"The output file is valid JSON"` — programmatically verifiable
- `"The bar chart has labeled axes"` — specific and observable
- `"The report includes at least 3 recommendations"` — countable

**Weak assertions:**
- `"The output is good"` — too vague
- `"The output uses exactly the phrase 'Total Revenue: $X'"` — too brittle

Add assertions to test cases:
```json
{
  "assertions": [
    "The output includes a bar chart image file",
    "The chart shows exactly 3 months",
    "Both axes are labeled",
    "The chart title mentions revenue"
  ]
}
```

---

## Grading Outputs

Grade each assertion as PASS or FAIL with specific evidence:

```json
{
  "assertion_results": [
    {
      "text": "Both axes are labeled",
      "passed": false,
      "evidence": "Y-axis labeled 'Revenue ($)' but X-axis has no label"
    }
  ],
  "summary": {
    "passed": 3,
    "failed": 1,
    "pass_rate": 0.75
  }
}
```

**Grading principles:**
- Require concrete evidence for a PASS. Don't give benefit of the doubt.
- Review the assertions themselves: are they too easy, too hard, or unverifiable? Fix these.
- For comparing versions: blind comparison (LLM judge without knowing which is which) removes bias.

---

## Benchmarking

```json
{
  "run_summary": {
    "with_skill": { "pass_rate": { "mean": 0.83 }, "time_seconds": { "mean": 45.0 } },
    "without_skill": { "pass_rate": { "mean": 0.33 }, "time_seconds": { "mean": 32.0 } },
    "delta": { "pass_rate": 0.50, "time_seconds": 13.0 }
  }
}
```

The `delta` tells you what the skill costs (more time, more tokens) and what it buys (higher pass rate).

---

## Analyzing Patterns

- **Assertions that always pass in both configurations**: remove — they test nothing
- **Assertions that always fail in both**: the assertion is broken, or the task is too hard
- **Assertions that pass with skill but fail without**: where the skill adds value — understand why
- **Inconsistent results (same eval passes sometimes, fails others)**: instructions may be ambiguous
- **Time/token outliers**: read the execution transcript to find the bottleneck

---

## The Iteration Loop

1. Give eval signals + current SKILL.md to an LLM, ask it to propose improvements
2. Review and apply changes
3. Rerun all test cases in a new `iteration-<N+1>/` directory
4. Grade and aggregate results
5. Review with a human
6. Repeat until: satisfied with results, feedback is consistently empty, or no meaningful improvement

**When prompting the LLM for improvements, include:**
- Generalize from feedback — fixes should address underlying issues broadly
- Keep the skill lean — fewer, better instructions often outperform exhaustive rules
- Explain the why — reasoning-based instructions work better than rigid directives
- Bundle repeated work — if every run reinvented similar logic, bundle it as a script

---

## Recommended Testing Scope

**Triggering tests** (does it load when it should?):
- Should trigger on obvious tasks
- Should trigger on paraphrased requests
- Should NOT trigger on unrelated topics

**Functional tests** (does it produce correct output?):
- Valid outputs generated
- API calls succeed
- Error handling works
- Edge cases covered

**Performance comparison** (is it better than baseline?):
- Token count with vs without skill
- Number of back-and-forth messages needed
- Failed/retried API calls
