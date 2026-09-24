TASK
Use the frozen task input below to complete the presentation task.

INPUT
{
  "query": "Prepare a 10-minute presentation outline about Workflow Template and Multi-Agent Workflow Builder MVP.",
  "user_id": "user_a"
}

CONTEXT / DATA
{
  "shared_context": {},
  "business_data": {
    "default_topic_ids": [
      "multi_agent_builder",
      "workflow_template"
    ],
    "topics": [
      {
        "id": "multi_agent_builder",
        "title": "Multi-Agent Workflow Builder",
        "keywords": [
          "multi-agent",
          "multi agent",
          "builder",
          "workflow builder",
          "agent builder"
        ],
        "points": [
          "A workflow builder turns a domain process into ordered nodes with defined inputs and outputs.",
          "The MVP generates executable Workflow JSON and uses sequential execution and trace output to make the result explainable."
        ],
        "slide_suggestions": [
          "Show Template -> Workflow JSON -> Engine -> Trace.",
          "Keep the demo under two minutes."
        ]
      },
      {
        "id": "workflow_template",
        "title": "Workflow Template",
        "keywords": [
          "template",
          "workflow",
          "node",
          "trace"
        ],
        "points": [
          "A template defines node order, node roles and required fields.",
          "The generated Workflow JSON is the contract between the builder and the execution engine."
        ],
        "slide_suggestions": [
          "Compare templates across domains.",
          "Use trace as proof that the template is executable."
        ]
      }
    ]
  }
}

CONSTRAINTS
{
  "duration_minutes": 10,
  "required_sections": [
    "opening",
    "problem",
    "architecture",
    "multi-domain evidence",
    "conclusion"
  ],
  "use_supplied_knowledge_only": true,
  "language": "English",
  "do_not_invent_facts": true
}

REQUIRED OUTPUT
{
  "required_fields": [
    "duration",
    "outline_sections",
    "evidence_points"
  ],
  "format": "section-by-section outline with evidence points"
}

MISSING INFORMATION RULE
Do not invent missing facts, data, policy details, weather, inventory, or model metadata. State what is missing when the supplied information is insufficient.

FIXTURE VERSION: presentation-2026-09-16-v2-10-minute
FIXTURE SHA256: bc3f34cd62224a68fd5d9d04fcbc06469c6426ca0d6af913f9576e62ff077295
