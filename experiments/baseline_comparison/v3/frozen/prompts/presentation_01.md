TASK
Use the frozen task input below to complete the presentation task.

INPUT
{
  "query": "Prepare a 15-minute presentation outline about Harness Engineering and Multi-Agent Workflow Builder MVP.",
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
        "id": "harness_engineering",
        "title": "Harness Engineering",
        "keywords": [
          "harness",
          "engineering",
          "agent framework",
          "execution structure"
        ],
        "points": [
          "Harness Engineering is the execution structure around an agent, including tools, memory, constraints, verification and feedback loops.",
          "It can make multi-agent development easier, so a project must explain what value remains beyond using a generic harness.",
          "The differentiating value should move from generic execution plumbing to domain-specific workflow templates and evidence."
        ],
        "slide_suggestions": [
          "Define Agent = Model + Harness.",
          "Show which harness parts are generic and which parts are project-specific.",
          "Use one defensive sentence that positions the MVP against generic harness tools."
        ]
      },
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
          "The MVP should show that templates can generate executable Workflow JSON instead of staying as static diagrams.",
          "Sequential execution and trace output make the result explainable during a presentation."
        ],
        "slide_suggestions": [
          "Show Template -> Workflow JSON -> Engine -> Trace.",
          "Use multiple domains to prove the builder is not hard-coded to one recommendation scenario.",
          "Keep the demo under two minutes by showing template selection and trace."
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
          "A template defines node order, node roles, required fields and builder equivalents.",
          "The generated Workflow JSON is the contract between the visual builder and the execution engine.",
          "Trace verifies that each node ran in the expected order and produced intermediate evidence."
        ],
        "slide_suggestions": [
          "Compare templates across domains.",
          "Highlight common structure and domain-specific nodes.",
          "Use trace as proof that the template is executable."
        ]
      }
    ]
  }
}

CONSTRAINTS
{
  "duration_minutes": 15,
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

FIXTURE VERSION: presentation-2026-09-16-v1
FIXTURE SHA256: 4d8bb302d1ea4dd207a13d02414e03069c7714406b8e85b85cb1bc8a32928aef
