# Workflow Analysis Templates

This directory contains templates for analyzing n8n workflows using OpenRouter API with the Mistral AI model. The templates are used by the workflow processor to generate comprehensive analysis reports.

## Template Files

- **combined_analysis.md**: Main template for comprehensive workflow analysis, including both technical and business aspects.
- **technical_analysis.md**: Template focused on technical aspects of the workflow.
- **business_vertical.md**: Template focused on business applications and industry verticals.

## Usage

The templates are used by the `n8n_workflow_processor.py` script to generate analysis reports. The script loads the template, renders it with workflow data, and sends it to the OpenRouter API for processing.

### Command Line Usage

```bash
python src/processors/n8n_workflow_processor.py <workflow_id> --template cline_docs/prompt_templates/combined_analysis.md
```

By default, the system uses the `mistralai/ministral-8b` model for analysis. You can specify a different model with the `--model` parameter:

```bash
python src/processors/n8n_workflow_processor.py <workflow_id> --template cline_docs/prompt_templates/combined_analysis.md --model mistralai/mistral-large
```

### Programmatic Usage

```python
from src.processors.n8n_workflow_processor import analyze_workflow
from src.utils.config import get_settings

# Analyze a workflow with a custom template
analysis_file = analyze_workflow(
    workflow_file="path/to/workflow.json",
    model=get_settings().default_model,  # Uses mistralai/ministral-8b by default
    template_path="cline_docs/prompt_templates/combined_analysis.md"
)
```

## Template Format

The templates use a simple placeholder format with `{{variable}}` syntax. The following variables are available:

- `{{workflow_json}}`: The full workflow JSON as a string.
- `{{nodes}}`: An array of node objects with `name` and `type` properties.

For the `{{nodes}}` array, you can use the following format to iterate over nodes:

```
{{#nodes}}
- **{{name}}** ({{type}}):
  - Description of the node
{{/nodes}}
```

## Testing

You can test the templates using the `test_template.py` script:

```bash
python test_template.py --workflow path/to/workflow.json
```

This will render the template with the specified workflow and generate an analysis report.

## Customization

You can customize the templates to focus on specific aspects of the workflow or to generate different types of analysis. The templates are written in Markdown format and can include any text or formatting that you want.

To create a new template, simply create a new Markdown file in the `prompt_templates` directory and use the placeholder syntax described above.
