import logging
from datetime import datetime
from typing import Dict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import structlog
import json

logger = structlog.get_logger("crawler")

class AsyncWebCrawler:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.driver = None
        self.page_data = {}
        self.setup_browser()

    def setup_browser(self):
        """Initialize the Selenium WebDriver with basic settings"""
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            logger.info("browser_initialized", job_id=self.job_id)
        except Exception as e:
            logger.error("browser_initialization_failed", 
                        job_id=self.job_id,
                        error=str(e))
            self.driver = None

    async def crawl(self, url: str):
        """Crawl a single webpage and extract data"""
        try:
            if self.driver is None:
                logger.error("browser_not_initialized", job_id=self.job_id)
                return

            logger.info("crawling_page", job_id=self.job_id, url=url)
            
            # Load the page
            self.driver.get(url)
            
            # Wait for body to be present
            wait = WebDriverWait(self.driver, 10)
            body = wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Extract data
            page_data = await self.extract_page_data(url, body)
            self.page_data[url] = page_data

        except Exception as e:
            logger.error("crawl_error",
                        job_id=self.job_id,
                        url=url,
                        error=str(e))
            self.page_data[url] = {
                'url': url,
                'error': str(e)
            }

    async def extract_page_data(self, url: str, body_element) -> Dict:
        """Extract structured data from a webpage"""
        try:
            # Get page HTML and full page source
            html = body_element.get_attribute('outerHTML')
            page_source = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Initialize structured data with page source
            data = {
                'page_source': page_source,
                'details': {
                    'nodes_used': {
                        'main': [],
                        'total_additional': 0
                    },
                    'title': self.driver.title,
                    'creator': {
                        'username': '',
                        'display_name': ''
                    },
                    'categories': [],
                    'published': ''
                },
                'description': {
                    'summary': '',
                    'workflow_steps': [],
                    'setup_requirements': []
                },
                'url': url,
                'n8n_template_details': '',
                'n8n_template_description': '',
                'n8n_workflow_json': ''
            }

            # Extract nodes used
            nodes_section = soup.find('div', class_='nodes-section')
            if nodes_section:
                main_nodes = nodes_section.find_all('div', class_='main-node')
                data['details']['nodes_used']['main'] = [node.text.strip() for node in main_nodes]
                additional_count = nodes_section.find('span', class_='additional-count')
                if additional_count:
                    count_text = additional_count.text.strip()
                    if count_text.startswith('+'):
                        data['details']['nodes_used']['total_additional'] = int(count_text[1:])

            # Extract creator info
            creator_section = soup.find('div', class_='creator-info')
            if creator_section:
                username = creator_section.find('span', class_='username')
                display_name = creator_section.find('span', class_='display-name')
                if username:
                    data['details']['creator']['username'] = username.text.strip()
                if display_name:
                    data['details']['creator']['display_name'] = display_name.text.strip()

            # Extract categories
            categories = soup.find_all('span', class_='category')
            data['details']['categories'] = [cat.text.strip() for cat in categories]

            # Extract publish date
            publish_date = soup.find('span', class_='publish-date')
            if publish_date:
                data['details']['published'] = publish_date.text.strip()

            # Extract description
            description = soup.find('div', class_='workflow-description')
            if description:
                summary = description.find('div', class_='summary')
                if summary:
                    data['description']['summary'] = summary.text.strip()
                steps = description.find_all('li', class_='workflow-step')
                data['description']['workflow_steps'] = [step.text.strip() for step in steps]

            # Extract setup requirements
            setup_section = soup.find('div', class_='setup-requirements')
            if setup_section:
                requirements = []
                for req in setup_section.find_all('div', class_='requirement'):
                    title = req.find('h3')
                    steps = req.find_all('li')
                    if title and steps:
                        requirements.append({
                            'title': title.text.strip(),
                            'steps': [step.text.strip() for step in steps]
                        })
                data['description']['setup_requirements'] = requirements

            # Extract n8n_template_details
            template_details = soup.select_one('#__layout > div > section > div.grid-container_WGQB2 > div.details-column_riLGn > div')
            if template_details:
                data['n8n_template_details'] = template_details.get_text(strip=True)
                logger.info("extracted_template_details", job_id=self.job_id, url=url)
            
            # Extract n8n_template_description
            template_description = soup.select_one('#__layout > div > section > div.grid-container_WGQB2 > div.template-column_G3Q-B > div.description_gTlAZ')
            if template_description:
                data['n8n_template_description'] = template_description.get_text(strip=True)
                logger.info("extracted_template_description", job_id=self.job_id, url=url)
            
            # Extract n8n_workflow_json using enhanced extraction methods
            try:
                # Get the page source
                page_source = self.driver.page_source
                
                # First try: Direct JSON pattern matching
                workflow_json = None
                json_pattern = r'\{\s*"nodes"\s*:\s*\[\s*\{\s*"parameters"[\s\S]*?"meta"\s*:\s*\{[\s\S]*?\}\s*\}'
                import re
                match = re.search(json_pattern, page_source)
                
                if match:
                    try:
                        workflow_json = json.loads(match.group(0))
                        logger.info("extracted_workflow_json_with_regex", job_id=self.job_id, url=url)
                    except json.JSONDecodeError:
                        logger.warning("regex_json_decode_failed", job_id=self.job_id, url=url)
                
                # Second try: DOM-based extraction
                if not workflow_json:
                    try:
                        # Look for workflow data in script tags
                        script_elements = self.driver.find_elements(By.CSS_SELECTOR, 'script#n8n-workflow-data[data-hypercontext="true"]')
                        
                        if not script_elements:
                            script_elements = self.driver.find_elements(By.CSS_SELECTOR, 'script[type="application/json"][data-n8n-workflow]')
                        
                        if script_elements:
                            script_content = script_elements[0].get_attribute('innerHTML')
                            if script_content:
                                # Clean up the script content
                                cleaned_content = script_content.replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>').replace('&#39;', "'").replace('&amp;', '&').replace('\\\"', '"').replace('\\n', '').replace('\\t', '')
                                
                                # Remove any JS variable assignment
                                cleaned_content = re.sub(r'^[^{]*', '', cleaned_content)
                                cleaned_content = re.sub(r'[^}]*$', '', cleaned_content)
                                
                                try:
                                    workflow_json = json.loads(cleaned_content)
                                    logger.info("extracted_workflow_json_from_script", job_id=self.job_id, url=url)
                                except json.JSONDecodeError:
                                    logger.warning("script_json_decode_failed", job_id=self.job_id, url=url)
                    except Exception as e:
                        logger.warning("dom_extraction_failed", job_id=self.job_id, url=url, error=str(e))
                
                # Third try: JavaScript execution
                if not workflow_json:
                    try:
                        js_result = self.driver.execute_script("""
                            // Try to find workflow data in window object
                            if (window.__NUXT__ && window.__NUXT__.state && window.__NUXT__.state.workflow) {
                                return JSON.stringify(window.__NUXT__.state.workflow);
                            }
                            
                            // Try to find in any global variable
                            for (var key in window) {
                                try {
                                    if (window[key] && typeof window[key] === 'object' && 
                                        window[key].nodes && Array.isArray(window[key].nodes) && 
                                        window[key].connections && typeof window[key].connections === 'object') {
                                        return JSON.stringify(window[key]);
                                    }
                                } catch (e) {
                                    // Skip inaccessible properties
                                    continue;
                                }
                            }
                            
                            // Try to find in data attributes
                            var elements = document.querySelectorAll('[data-workflow]');
                            for (var i = 0; i < elements.length; i++) {
                                try {
                                    var workflowData = elements[i].getAttribute('data-workflow');
                                    if (workflowData) {
                                        var parsed = JSON.parse(workflowData);
                                        if (parsed.nodes && parsed.connections) {
                                            return workflowData;
                                        }
                                    }
                                } catch (e) {
                                    continue;
                                }
                            }
                            
                            return '';
                        """)
                        
                        if js_result and js_result != '':
                            try:
                                workflow_json = json.loads(js_result)
                                logger.info("extracted_workflow_json_from_javascript", job_id=self.job_id, url=url)
                            except json.JSONDecodeError:
                                logger.warning("javascript_json_decode_failed", job_id=self.job_id, url=url)
                    except Exception as js_error:
                        logger.warning("javascript_extraction_failed", job_id=self.job_id, url=url, error=str(js_error))
                
                # Fourth try: Look for workflow in n8n_workflow_json field
                if not workflow_json:
                    workflow_json_pattern = r'"n8n_workflow_json"\s*:\s*"([\s\S]*?)"'
                    workflow_json_match = re.search(workflow_json_pattern, page_source)
                    
                    if workflow_json_match and workflow_json_match.group(1):
                        try:
                            # This is likely a string representation, try to extract JSON from it
                            json_extract = re.search(r'\{\s*"nodes"\s*:\s*\[[\s\S]*?\}\s*\}', workflow_json_match.group(1))
                            if json_extract:
                                workflow_json = json.loads(json_extract.group(0))
                                logger.info("extracted_workflow_json_from_field", job_id=self.job_id, url=url)
                        except Exception as e:
                            logger.warning("n8n_workflow_json_extraction_failed", job_id=self.job_id, url=url, error=str(e))
                
                # If we found a workflow JSON, validate and convert it to a string
                if workflow_json and isinstance(workflow_json, dict) and 'nodes' in workflow_json and 'connections' in workflow_json:
                    # Validate nodes have required technical fields
                    has_valid_nodes = any(
                        node.get('id') and 
                        node.get('type') and 
                        isinstance(node.get('parameters'), dict) and 
                        isinstance(node.get('position'), list)
                        for node in workflow_json.get('nodes', [])
                    )
                    
                    if has_valid_nodes:
                        # Add metadata and structure
                        structured_data = {
                            "metadata": {
                                "source_url": url,
                                "extracted_at": datetime.utcnow().isoformat() + "Z",
                                "schema_version": "1.1"
                            },
                            "workflow": workflow_json
                        }
                        data['n8n_workflow_json'] = json.dumps(structured_data)
                        logger.info("valid_workflow_json_extracted", job_id=self.job_id, url=url)
                    else:
                        logger.warning("invalid_node_structure", job_id=self.job_id, url=url)
                else:
                    # If all else fails, extract workflow-related text
                    workflow_text = []
                    for element in soup.find_all(text=lambda text: text and 'workflow' in text.lower()):
                        parent = element.parent
                        if parent.name not in ['script', 'style']:
                            workflow_text.append(element.strip())
                    
                    if workflow_text:
                        data['n8n_workflow_json'] = "Workflow information: " + " | ".join(workflow_text[:10])
                        logger.info("extracted_workflow_text", job_id=self.job_id, url=url)
            except Exception as e:
                logger.warning("workflow_json_extraction_failed", job_id=self.job_id, url=url, error=str(e))

            return data

        except Exception as e:
            logger.error("data_extraction_failed",
                        job_id=self.job_id,
                        url=url,
                        error=str(e))
            return {
                'url': url,
                'error': str(e),
                'n8n_template_details': '',
                'n8n_template_description': '',
                'n8n_workflow_json': ''
            }
    
    def extract_workflow_from_element(self, element):
        """Extract workflow JSON from a DOM element"""
        try:
            # Try to find node elements
            nodes = []
            node_elements = element.find_elements(By.CSS_SELECTOR, "[data-node-name]")
            
            if not node_elements:
                node_elements = element.find_elements(By.CSS_SELECTOR, "[data-test-id='canvas-node']")
            
            if not node_elements:
                return None
            
            # Extract node data
            for node_element in node_elements:
                try:
                    node_name = node_element.get_attribute("data-node-name")
                    node_type = node_element.get_attribute("data-node-type")
                    node_id = node_element.get_attribute("data-id")
                    
                    if not node_name or not node_id:
                        continue
                    
                    # Extract position from style attribute or transform
                    style = node_element.get_attribute("style")
                    position = [0, 0]
                    if style and "transform: translate(" in style:
                        transform = style.split("transform: translate(")[1].split(")")[0]
                        if transform:
                            coords = transform.replace("px", "").split(",")
                            if len(coords) >= 2:
                                position = [int(float(coords[0].strip())), int(float(coords[1].strip()))]
                    
                    # Create node object
                    node = {
                        "id": node_id,
                        "name": node_name,
                        "type": node_type or "unknown",
                        "position": position,
                        "parameters": {}
                    }
                    
                    nodes.append(node)
                except Exception as node_error:
                    logger.warning("node_extraction_failed", error=str(node_error))
            
            # Try to find connections
            connections = {}
            edge_elements = element.find_elements(By.CSS_SELECTOR, "[data-test-id='edge']")
            
            for edge_element in edge_elements:
                try:
                    source_node = edge_element.get_attribute("data-source-node-name")
                    target_node = edge_element.get_attribute("data-target-node-name")
                    
                    if not source_node or not target_node:
                        continue
                    
                    if source_node not in connections:
                        connections[source_node] = {"main": [[]]}
                    
                    connections[source_node]["main"][0].append({
                        "node": target_node,
                        "type": "main",
                        "index": 0
                    })
                except Exception as edge_error:
                    logger.warning("edge_extraction_failed", error=str(edge_error))
            
            # If we have nodes and connections, create the workflow JSON
            if nodes and connections:
                return {
                    "nodes": nodes,
                    "connections": connections,
                    "pinData": {},
                    "meta": {
                        "instanceId": "extracted-workflow-" + self.job_id
                    }
                }
            
            return None
        except Exception as e:
            logger.warning("workflow_extraction_failed", error=str(e))
            return None

    def close(self):
        """Close the browser and clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("browser_closed", job_id=self.job_id)
            except Exception as e:
                logger.error("browser_close_failed",
                           job_id=self.job_id,
                           error=str(e))
            finally:
                self.driver = None
