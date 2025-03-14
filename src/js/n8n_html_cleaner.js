/**
 * N8N Code Node for cleaning up scraped HTML from workflow details
 * 
 * This code can be used in an N8N "Code" node to clean up the HTML content
 * returned from the scraping API.
 * 
 * Input: The JSON response from the scraping API
 * Output: A cleaned and structured version of the workflow data
 */

// N8N Code Node function
function processData(items) {
  // Process each item in the input array
  return items.map(item => {
    // Get the data from the HTTP Request node
    const data = item.json;
    
    // Clean and structure the data
    const cleanedData = cleanWorkflowData(data);
    
    // Return the cleaned data
    return {
      json: cleanedData
    };
  });
}

/**
 * Clean and structure the workflow data
 */
function cleanWorkflowData(data) {
  const result = {
    url: data.url,
    status: data.status
  };
  
  // Extract workflow details
  if (data.workflow_details) {
    result.details = extractWorkflowDetails(data.workflow_details);
  }
  
  // Extract workflow description
  if (data.workflow_description) {
    result.description = extractWorkflowDescription(data.workflow_description);
  }
  
  // Extract workflow demo JSON if present
  if (data.workflow_demo) {
    const demoJson = extractWorkflowDemoJson(data.workflow_demo);
    if (demoJson) {
      result.demo = demoJson;
    } else {
      result.has_demo = true;
    }
  }
  
  return result;
}

/**
 * Extract the n8n workflow JSON from the demo HTML
 */
function extractWorkflowDemoJson(html) {
  if (!html) return null;

  // Match the specific DIV hierarchy with dynamic class suffixes
  const workflowContainerMatch = html.match(
    /<div[^>]*class="[^"]*grid-container[^"]*"[^>]*>[\s\S]*?<div[^>]*class="[^"]*template-column[^"]*"[^>]*>[\s\S]*?<div[^>]*class="[^"]*workflow-preview[^"]*"[^>]*>([\s\S]*?)<\/div>/i
  );

  if (workflowContainerMatch && workflowContainerMatch[1]) {
    const containerHtml = workflowContainerMatch[1];
    
    // First try to extract iframe URL
    const iframeMatch = containerHtml.match(/<iframe[^>]*src="(https?:\/\/[^"]+)"/i);
    if (iframeMatch) {
      return { iframe_url: iframeMatch[1] };
    }

    // Then try to extract inline JSON
    const jsonMatch = containerHtml.match(/({"nodes"\s*:\s*\[[\s\S]*?}\s*\]\s*}[^<]*)/i);
    if (jsonMatch) {
      try {
        const decodedJson = decodeHTMLEntities(jsonMatch[1]);
        const workflowData = JSON.parse(decodedJson);
        if (workflowData.nodes) {
          return workflowData;
        }
      } catch (error) {
        console.log('JSON parsing error:', error);
      }
    }

    // Fallback to raw HTML capture
    return { 
      raw_html: containerHtml,
      structure_match: true,
      extracted_at: new Date().toISOString()
    };
  }

  // Fallback to looking for workflow data in a data attribute
  const workflowDataMatch = html.match(/data-workflow="([^"]*)"/i);
  if (workflowDataMatch && workflowDataMatch[1]) {
    try {
      // The data might be HTML-encoded, so we need to decode it
      const workflowData = decodeHTMLEntities(workflowDataMatch[1]);
      return JSON.parse(workflowData);
    } catch (error) {
      console.log('Error parsing workflow data attribute:', error);
    }
  }
  
  // Look for workflow data in a script tag
  const scriptMatch = html.match(/<script[^>]*>([\s\S]*?)<\/script>/i);
  if (scriptMatch && scriptMatch[1]) {
    try {
      const scriptContent = scriptMatch[1].trim();
      // Try to find a JSON object in the script content
      const jsonMatch = scriptContent.match(/({[\s\S]*})/);
      if (jsonMatch && jsonMatch[1]) {
        return JSON.parse(jsonMatch[1]);
      }
    } catch (error) {
      console.log('Error parsing script content:', error);
    }
  }
  
  // Look for workflow data in a JSON string within the HTML
  const jsonMatch = html.match(/({[\s\S]*"nodes"[\s\S]*})/);
  if (jsonMatch && jsonMatch[1]) {
    try {
      return JSON.parse(jsonMatch[1]);
    } catch (error) {
      console.log('Error parsing JSON string:', error);
    }
  }
  
  // If we can't find the JSON data directly, try to extract it from the n8n-demo element
  try {
    // Look for any JSON-like structure with "nodes" property which is typical for n8n workflows
    const nodesMatch = html.match(/"nodes"\s*:\s*\[[\s\S]*?\]/);
    if (nodesMatch && nodesMatch[0]) {
      // Try to reconstruct a valid JSON object
      const jsonStr = '{' + nodesMatch[0] + '}';
      return JSON.parse(jsonStr);
    }
  } catch (error) {
    console.log('Error extracting nodes property:', error);
  }
  
  return null;
}

/**
 * Extract structured data from workflow details HTML
 */
function extractWorkflowDetails(html) {
  if (!html) return null;
  
  const result = {};
  
  // Extract title
  const titleMatch = html.match(/<h1[^>]*>(.*?)<\/h1>/i);
  if (titleMatch && titleMatch[1]) {
    result.title = cleanText(titleMatch[1]);
  }
  
  // Extract publication date
  const pubDateMatch = html.match(/<p>([^<]*)<\/p>/i);
  if (pubDateMatch && pubDateMatch[1]) {
    result.published = cleanText(pubDateMatch[1]);
  }
  
  // Extract creator info
  const creatorInfo = {};
  const usernameMatch = html.match(/class="username_[^"]*"[^>]*>\s*([^<]*)\s*</i);
  if (usernameMatch && usernameMatch[1]) {
    creatorInfo.username = cleanText(usernameMatch[1]);
  }
  
  // Check if verified
  if (html.includes('verified-icon') || html.includes('verified v-popper')) {
    creatorInfo.verified = true;
  }
  
  if (Object.keys(creatorInfo).length > 0) {
    result.creator = creatorInfo;
  }
  
  // Extract categories
  const categories = [];
  const categoryRegex = /class="category-badge_[^"]*"[^>]*>\s*([^<]*)\s*</g;
  let categoryMatch;
  while ((categoryMatch = categoryRegex.exec(html)) !== null) {
    if (categoryMatch[1]) {
      categories.push(cleanText(categoryMatch[1]));
    }
  }
  
  if (categories.length > 0) {
    result.categories = categories;
  }
  
  // Extract integrations/apps
  const integrations = [];
  const appRegex = /href="\/integrations\/([^\/"]*)\/"/g;
  let appMatch;
  while ((appMatch = appRegex.exec(html)) !== null) {
    if (appMatch[1]) {
      integrations.push(appMatch[1]);
    }
  }
  
  if (integrations.length > 0) {
    result.integrations = integrations;
  }
  
  return result;
}

/**
 * Extract cleaned text from workflow description HTML
 */
function extractWorkflowDescription(html) {
  if (!html) return null;
  
  // Remove all HTML tags and decode HTML entities
  let text = html.replace(/<[^>]*>/g, ' ');
  
  // Clean up the text
  text = cleanText(text);
  
  return text;
}

/**
 * Clean text by removing extra whitespace and HTML entities
 */
function cleanText(text) {
  if (!text) return '';
  
  // Replace HTML entities
  text = decodeHTMLEntities(text);
  
  // Remove extra whitespace
  text = text.replace(/\s+/g, ' ').trim();
  
  return text;
}

/**
 * Decode HTML entities in a string
 */
function decodeHTMLEntities(text) {
  if (!text) return '';
  
  return text
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/&#(\d+);/g, (match, dec) => String.fromCharCode(dec));
}

// This is required for N8N to recognize the function
return processData($input.all());
