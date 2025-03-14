/**
 * N8N Workflow Validator and Formatter
 * 
 * This script ensures that extracted workflow JSON is compliant with n8n's requirements.
 * It validates the structure and adds any missing required fields.
 * 
 * Usage in n8n Code node:
 * 1. Add this code to a Function node after your HTTP Request node
 * 2. Connect the HTTP Request node output to this Function node
 */

// N8N Code Node function
function processData(items) {
  // Process each item in the input array
  return items.map(item => {
    // Get the data from the HTTP Request node
    const data = item.json;
    
    // If the data has a demo property (from our API server's clean=true parameter)
    if (data.demo) {
      // Validate and format the workflow JSON
      const formattedWorkflow = ensureN8nCompliance(data.demo);
      
      // Return the formatted workflow
      return {
        json: formattedWorkflow
      };
    }
    
    // If no demo property, return the original data
    return item;
  });
}

/**
 * Enhanced JSON extraction with fallback strategies
 */
const cheerio = require('cheerio');
const WORKFLOW_SCRIPT_SELECTOR = 'script#n8n-workflow-data[data-hypercontext="true"]';

function extractWorkflowJson(html) {
  // First try: Direct JSON pattern matching
  const jsonPattern = /\{\s*"nodes"\s*:\s*\[\s*\{\s*"parameters"[\s\S]*?"meta"\s*:\s*\{[\s\S]*?\}\s*\}/g;
  const match = html.match(jsonPattern);
  
  if (match) {
    try {
      const workflow = JSON.parse(match[0]);
      if (isValidWorkflowStructure(workflow)) {
        return workflow;
      }
    } catch (e) {
      console.error("Direct JSON parse failed:", e.message);
    }
  }
  
  // Second try: DOM-based extraction
  try {
    const $ = cheerio.load(html);
    const scriptContent = $(WORKFLOW_SCRIPT_SELECTOR).html();
    
    if (scriptContent) {
      // Decode HTML entities and clean JS wrappers
      const decodedContent = scriptContent
        .replace(/&quot;/g, '"')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&#39;/g, "'")
        .replace(/&amp;/g, '&')
        .replace(/\\"/g, '"')
        .replace(/\\n/g, '')
        .replace(/\\t/g, '')
        .replace(/^[^{]*/, '') // Remove any JS variable assignment
        .replace(/[^}]*$/, ''); // Remove trailing semicolons
      
      try {
        const workflow = JSON.parse(decodedContent);
        if (isValidWorkflowStructure(workflow)) {
          return workflow;
        }
      } catch (e) {
        console.error("Script content parse failed:", e.message);
      }
    }
  } catch (e) {
    console.error("DOM extraction failed:", e.message);
  }
  
  // Third try: Look for workflow in n8n_workflow_json field
  const workflowJsonPattern = /"n8n_workflow_json"\s*:\s*"([\s\S]*?)"/;
  const workflowJsonMatch = html.match(workflowJsonPattern);
  
  if (workflowJsonMatch && workflowJsonMatch[1]) {
    try {
      // This is likely a string representation, try to extract JSON from it
      const jsonExtract = workflowJsonMatch[1].match(/\{\s*"nodes"\s*:\s*\[[\s\S]*?\}\s*\}/);
      if (jsonExtract) {
        const workflow = JSON.parse(jsonExtract[0]);
        if (isValidWorkflowStructure(workflow)) {
          return workflow;
        }
      }
    } catch (e) {
      console.error("n8n_workflow_json extraction failed:", e.message);
    }
  }
  
  // Final fallback: Try to extract from any malformed JSON
  return extractFromMalformedJSON(html);
}

function isValidWorkflowStructure(workflow) {
  // Check for required workflow structure
  if (!workflow || !Array.isArray(workflow.nodes) || typeof workflow.connections !== 'object') {
    return false;
  }
  
  // Validate nodes have required technical fields
  const hasValidNodes = workflow.nodes.some(node => 
    node.id && 
    node.type && 
    node.type.match(/(@n8n\/|n8n-nodes-base\.)/) && 
    typeof node.parameters === 'object' && 
    Array.isArray(node.position)
  );
  
  // Validate meta
  const hasValidMeta = workflow.meta && 
                      typeof workflow.meta === 'object' && 
                      workflow.meta.instanceId;
  
  return hasValidNodes && hasValidMeta;
}

function extractFromMalformedJSON(jsonStr) {
  try {
    // Attempt cleanup of common JSON issues
    const cleaned = jsonStr
      .replace(/\\"/g, '"')
      .replace(/\\n/g, '')
      .replace(/\\t/g, '')
      .replace(/'/g, '"');
      
    return JSON.parse(cleaned);
  } catch (e) {
    return null;
  }
}

/**
 * Validate workflow JSON structure
 */
function isValidWorkflowJson(jsonStr) {
  try {
    const data = JSON.parse(jsonStr);
    return data && typeof data === 'object' && 
           'nodes' in data && Array.isArray(data.nodes);
  } catch {
    return false;
  }
}

/**
 * Ensure the workflow JSON is compliant with n8n requirements
 */
function ensureN8nCompliance(workflow) {
  // Create a new object with all required fields
  const compliantWorkflow = {
    // Ensure nodes array exists (required)
    nodes: workflow.nodes || [],
    
    // Ensure connections object exists (required)
    connections: workflow.connections || {},
    
    // Ensure pinData object exists (required)
    pinData: workflow.pinData || {},
    
    // Ensure meta object exists (required)
    meta: workflow.meta || {
      instanceId: workflow.meta?.instanceId || generateInstanceId()
    }
  };
  
  // Validate nodes structure
  compliantWorkflow.nodes = compliantWorkflow.nodes.map(node => {
    // Ensure each node has required properties
    return {
      id: node.id || generateId(),
      name: node.name || "Unnamed Node",
      type: node.type || "unknown",
      position: node.position || [0, 0],
      parameters: node.parameters || {},
      typeVersion: node.typeVersion || 1,
      ...node // Keep any other properties
    };
  });
  
  // Return the compliant workflow
  return compliantWorkflow;
}

/**
 * Generate a random ID for nodes
 */
function generateId() {
  return Math.random().toString(36).substring(2, 15) + 
         Math.random().toString(36).substring(2, 15);
}

/**
 * Generate a random instance ID
 */
function generateInstanceId() {
  return Array.from({ length: 40 }, () => 
    Math.floor(Math.random() * 16).toString(16)
  ).join('');
}

// This is required for N8N to recognize the function
return processData($input.all());
