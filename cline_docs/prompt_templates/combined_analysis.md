# Comprehensive Workflow Analysis for "{{workflow_name}}"

You are a workflow analysis expert. Analyze the following n8n workflow JSON in detail:

```json
{{workflow_json}}
```

## Required Analysis Sections

### 1. Node Analysis
Provide a detailed examination of each node's purpose, configuration, and role in the workflow. Ensure you analyze ALL nodes present in the workflow:

{{#nodes}}
- **{{name}}** ({{type}}):
  - **Type**: {{type}}
  - **Purpose**: What is this node designed to do in the workflow?
  - **Configuration**: What are the key configuration parameters?
  - **Input/Output**: What data does this node receive and produce?
  - **Role**: How does this node contribute to the overall workflow?
{{/nodes}}

### 2. Flow Analysis
- Trace how data flows through the workflow by following the connections
- Identify key connection points and dependencies between nodes
- Highlight any potential bottlenecks or optimization opportunities
- Analyze error handling and fallback mechanisms
- Describe the complete data flow from trigger to final output

### 3. Business Vertical
Identify at least 3-5 potential industry verticals where this workflow could be applied:

- **Industry 1**:
  - Why this workflow is relevant to this industry (be specific)
  - Specific use cases within this industry (at least 2-3 examples)
  - Business benefits for this industry (quantifiable if possible)
  - Any modifications needed for this industry

- **Industry 2**:
  - Why this workflow is relevant to this industry (be specific)
  - Specific use cases within this industry (at least 2-3 examples)
  - Business benefits for this industry (quantifiable if possible)
  - Any modifications needed for this industry

- **Industry 3**:
  - Why this workflow is relevant to this industry (be specific)
  - Specific use cases within this industry (at least 2-3 examples)
  - Business benefits for this industry (quantifiable if possible)
  - Any modifications needed for this industry

### 4. Use Cases
- Primary intended use case for this workflow (be very specific)
- The business problem it solves (describe the pain points)
- Target users or roles who would benefit from this workflow
- Key business benefits (efficiency, cost savings, etc.)
- Additional potential applications of this workflow
- How it could be adapted for different scenarios

### 5. Technical Details
- **API Endpoints**: Identify any external API endpoints used
- **Data Structures**: Describe key data structures and formats
- **Integration Points**: List systems or services this workflow integrates with
- **Technical Specifications**: Note any specific technical requirements or limitations
- **Security Considerations**: Identify authentication methods and security practices
- **Database Interactions**: Describe how the workflow interacts with databases

### 6. Vector Database Enrichment
- **Technical Keywords**: List at least 15-20 technical terms relevant to this workflow
- **Concepts**: Identify key technical concepts demonstrated
- **Patterns**: Note any design patterns or architectural approaches used
- **Technologies**: List all technologies and frameworks used

Format your response as a structured report with clear sections and bullet points. Ensure your analysis is comprehensive and covers ALL nodes in the workflow.
