#!/usr/bin/env python3
"""
AMBOSS Content Scraper

A specialized scraper for extracting learning content from AMBOSS medical articles.
Automatically handles authentication, content expansion, and exports to multiple formats.

Features:
- Selenium-based dynamic content interaction with smart expansion
- Automatic login and session management
- Rich HTML content extraction with proper formatting
- Support for text, markdown, and HTML output formats
- Batch processing with rate limiting and session reuse
- Comprehensive content extraction including tables, images, and content boxes
- Optional debug output for troubleshooting

Usage:
    # Single article
    python amboss_scraper.py "https://next.amboss.com/us/article/abc123"
    
    # Batch processing with authentication
    python amboss_scraper.py -u urls.txt --username user@example.com --password pass
    
    # HTML output with debug
    python amboss_scraper.py -u urls.txt -f html -o output/ --debug

Requirements:
    - Python 3.6+
    - Selenium WebDriver
    - Chrome/Chromium browser
    - BeautifulSoup4

Author: AI Assistant
Version: 2.1
License: MIT License - see LICENSE file for details
"""

import sys
import os
import time
import random
import re
import argparse
from bs4 import BeautifulSoup

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("ERROR: Selenium is required for this scraper.")
    print("Install with: pip install selenium")
    sys.exit(1)


class AmbossScraper:
    """Main scraper class for AMBOSS content extraction"""
    
    def __init__(self, username=None, password=None, debug=False):
        """
        Initialize the AMBOSS scraper
        
        Args:
            username: Email for AMBOSS authentication
            password: Password for AMBOSS authentication  
            debug: Enable debug output and file saving
        """
        self.username = username
        self.password = password
        self.debug = debug
        self.driver = None
        self.debug_dir = None
        
        # Setup debug directory if needed
        if self.debug:
            self.debug_dir = "debug_amboss"
            if not os.path.exists(self.debug_dir):
                os.makedirs(self.debug_dir)
                self._debug_print(f"Created debug directory: {self.debug_dir}")
    
    def _debug_print(self, message):
        """Print debug messages if debug mode is enabled"""
        if self.debug:
            print(f"DEBUG: {message}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver with optimal settings"""
        if not SELENIUM_AVAILABLE:
            raise Exception("Selenium not available")
        
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self._debug_print("WebDriver setup successful")
            return True
        except Exception as e:
            print(f"ERROR: Could not setup WebDriver: {e}")
            print("Make sure Chrome/Chromium is installed and chromedriver is in PATH")
            return False
    
    def cleanup(self):
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
                self._debug_print("WebDriver cleaned up")
            except:
                pass
            self.driver = None
    
    def login(self):
        """
        Authenticate with AMBOSS
        
        Returns:
            bool: True if login successful, False otherwise
        """
        if not self.username or not self.password:
            self._debug_print("No credentials provided, skipping login")
            return True
        
        if not self.driver:
            if not self.setup_driver():
                return False
        
        try:
            login_url = "https://next.amboss.com/us/login"
            self._debug_print(f"Navigating to login page: {login_url}")
            self.driver.get(login_url)
            
            # Wait for page load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            if self.debug and self.debug_dir:
                with open(f"{self.debug_dir}/login_page.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
            
            # Wait for and find login fields
            self._debug_print("Looking for login fields...")
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            # Enter credentials
            self._debug_print("Entering credentials...")
            email_field.clear()
            email_field.send_keys(self.username)
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Find and click login button
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Log in']"))
            )
            
            self._debug_print("Clicking login button...")
            self.driver.execute_script("arguments[0].click();", login_button)
            
            # Wait for login to complete
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda driver: 'login' not in driver.current_url.lower()
                )
                self._debug_print(f"Login successful - redirected to: {self.driver.current_url}")
                return True
            except TimeoutException:
                if 'login' in self.driver.current_url.lower():
                    print("ERROR: Login failed - still on login page")
                    return False
                else:
                    self._debug_print("Login appears successful")
                    return True
                    
        except Exception as e:
            print(f"ERROR: Login failed: {e}")
            return False
    
    def expand_content(self):
        """
        Smart content expansion that ensures sections end up in expanded state
        
        Returns:
            bool: True if expansion was attempted, False otherwise
        """
        try:
            # First, try to find and click any available toggle buttons
            success = self._try_all_toggle_methods()
            if success:
                return True
            
            self._debug_print("No expansion method worked - content may already be expanded or structure changed")
            return False
            
        except Exception as e:
            self._debug_print(f"Error during content expansion: {e}")
            return False
    
    def _try_all_toggle_methods(self):
        """Try multiple methods to expand content"""
        
        # Method 1: Try global toggle button
        if self._try_global_toggle_button():
            return True
        
        # Method 2: Try buttons with aria-expanded attribute
        if self._try_aria_expanded_buttons():
            return True
        
        # Method 3: Try individual section headers
        if self._try_section_headers():
            return True
        

        
        return False
    
    def _try_global_toggle_button(self):
        """Try to find and use a global toggle button"""
        try:
            toggle_selectors = [
                '[data-e2e-test-id="toggle-all-sections-button"]',
                'button[aria-label*="toggle"]',
                'button[aria-label*="expand"]',
                'button[aria-label*="collapse"]',
                '[data-testid*="toggle"]'
            ]
            
            for selector in toggle_selectors:
                try:
                    toggle_button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    self._debug_print(f"Found global toggle button: {selector}")
                    
                    # Click to expand (assume it will expand if collapsed)
                    toggle_button.click()
                    time.sleep(2)
                    
                    # Check if content appeared
                    if self._check_content_visibility():
                        self._debug_print("Global toggle successful")
                        return True
                    
                    # If no content appeared, try clicking again
                    toggle_button.click()
                    time.sleep(2)
                    
                    if self._check_content_visibility():
                        self._debug_print("Global toggle successful after second click")
                        return True
                        
                except (TimeoutException, NoSuchElementException):
                    continue
            
            return False
            
        except Exception as e:
            self._debug_print(f"Error with global toggle: {e}")
            return False
    
    def _try_aria_expanded_buttons(self):
        """Try buttons with aria-expanded attribute"""
        try:
            # Find buttons that might be collapsed
            buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[aria-expanded]')
            
            if not buttons:
                return False
            
            self._debug_print(f"Found {len(buttons)} buttons with aria-expanded")
            
            clicked_any = False
            for button in buttons:
                try:
                    aria_expanded = button.get_attribute('aria-expanded')
                    self._debug_print(f"Button aria-expanded: {aria_expanded}")
                    
                    if aria_expanded == 'false':
                        self._debug_print(f"Clicking collapsed button (aria-expanded=false)")
                        self.driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)
                        clicked_any = True
                    elif aria_expanded == 'true':
                        # Try clicking expanded buttons too - might toggle to expand more
                        self._debug_print(f"Clicking expanded button to see if it toggles more content")
                        self.driver.execute_script("arguments[0].click();", button)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", button)
                        time.sleep(1)
                        clicked_any = True
                        
                except Exception as e:
                    self._debug_print(f"Error clicking aria-expanded button: {e}")
                    continue
            
            if clicked_any:
                time.sleep(2)
                # Always return True if we clicked something - let the extraction handle it
                self._debug_print("Clicked aria-expanded buttons")
                return True
            
            return False
            
        except Exception as e:
            self._debug_print(f"Error with aria-expanded buttons: {e}")
            return False
    
    def _try_section_headers(self):
        """Try clicking on section headers to expand them"""
        try:
            # Find section headers that might be clickable
            header_selectors = [
                '[data-e2e-test-id="section-with-header"] [role="button"]',
                '[data-e2e-test-id="section-with-header"] button',
                '[data-e2e-test-id="section-with-header"] h3',
                '[data-e2e-test-id="section-with-header"] h4',
                '[data-e2e-test-id="section-with-header"] [class*="header"]'
            ]
            
            clicked_any = False
            for selector in header_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self._debug_print(f"Clicking {len(elements)} elements with selector: {selector}")
                        
                        for i, element in enumerate(elements):
                            try:
                                if element.is_displayed():
                                    self._debug_print(f"Clicking element {i+1}/{len(elements)}")
                                    self.driver.execute_script("arguments[0].click();", element)
                                    time.sleep(0.3)
                                    clicked_any = True
                            except Exception as e:
                                self._debug_print(f"Error clicking element {i+1}: {e}")
                                continue
                except Exception as e:
                    self._debug_print(f"Error with selector {selector}: {e}")
                    continue
            
            if clicked_any:
                time.sleep(2)
                # Always return True if we clicked something
                self._debug_print("Clicked section headers")
                return True
            
            return False
            
        except Exception as e:
            self._debug_print(f"Error with section headers: {e}")
            return False
    
    def _check_content_visibility(self):
        """Check if content sections are now visible"""
        try:
            # Look for visible content containers
            visible_content = self.driver.find_elements(
                By.CSS_SELECTOR, 
                '[data-e2e-test-id="section-content-is-shown"]'
            )
            
            if visible_content:
                self._debug_print(f"Found {len(visible_content)} visible content sections")
                return True
            
            # Also check for any content that might be visible
            sections = self.driver.find_elements(
                By.CSS_SELECTOR, 
                '[data-e2e-test-id="section-with-header"]'
            )
            
            visible_sections = 0
            for section in sections:
                try:
                    # Check if section has substantial text content
                    text_content = section.text.strip()
                    if text_content and len(text_content) > 50:  # Reasonable content length
                        visible_sections += 1
                except:
                    continue
            
            if visible_sections > 0:
                self._debug_print(f"Found {visible_sections} sections with substantial content")
                return True
            
            return False
            
        except Exception as e:
            self._debug_print(f"Error checking content visibility: {e}")
            return False
    
    def extract_article_title(self, html_content):
        """
        Extract article title from the page
        
        Args:
            html_content (str): HTML content of the page
            
        Returns:
            str or None: Article title if found, None otherwise
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the article header element
        article_header = soup.find(attrs={'data-e2e-test-id': 'articleHeader'})
        
        if article_header:
            # Try to find the title in various locations within the header
            title_element = (
                article_header.find('h1') or 
                article_header.find('h2') or 
                article_header.find(class_=lambda x: x and 'title' in x.lower()) or
                article_header
            )
            
            if title_element:
                title = self.clean_text(title_element.get_text())
                self._debug_print(f"Found article title: {title}")
                return title
        
        self._debug_print("Could not find article title")
        return None
    
    def extract_section_title(self, section):
        """
        Extract section title with improved logic for various page structures
        """
        # Try multiple strategies to find the section title
        
        # Strategy 1: Look for data-e2e-test-id="particle-header"
        header_element = section.find('div', {'data-e2e-test-id': 'particle-header'})
        if header_element:
            h3_element = header_element.find('h3')
            if h3_element:
                title = self.clean_text(h3_element.get_text())
                if title:
                    return title
        
        # Strategy 2: Look for any h3 in header area
        header_container = section.find('div', class_=lambda x: x and 'header' in x.lower())
        if header_container:
            h3_element = header_container.find('h3')
            if h3_element:
                title = self.clean_text(h3_element.get_text())
                if title:
                    return title
        
        # Strategy 3: Look for any h3 in the section
        h3_element = section.find('h3')
        if h3_element:
            title = self.clean_text(h3_element.get_text())
            if title:
                return title
        
        # Strategy 4: Look for button or clickable element with text
        button_elements = section.find_all(['button', 'div'], class_=lambda x: x and any(
            keyword in x.lower() for keyword in ['header', 'title', 'button']
        ))
        for button in button_elements:
            text = self.clean_text(button.get_text())
            if text and len(text) < 100:  # Reasonable title length
                return text
        
        # Strategy 5: Look for any text in header-like elements
        for elem in section.find_all(['div', 'span'], limit=10):
            if elem.get('class'):
                classes = ' '.join(elem.get('class', []))
                if any(keyword in classes.lower() for keyword in ['header', 'title']):
                    text = self.clean_text(elem.get_text())
                    if text and 5 < len(text) < 100:
                        return text
        
        return None
    
    def extract_sections(self, soup):
        """Extract sections from the page with comprehensive content processing"""
        sections = []
        
        # Extract article title first
        article_title = self.extract_article_title_from_soup(soup)
        
        # Find all sections with the specific data attribute
        section_elements = soup.find_all('section', {'data-e2e-test-id': 'section-with-header'})
        
        if self.debug:
            print(f"DEBUG: Found {len(section_elements)} sections with section-with-header")
        
        for i, section in enumerate(section_elements):
            section_data = {}
            
            # Extract section title
            title = self.extract_section_title_from_element(section)
            if title:
                section_data['title'] = title
            else:
                section_data['title'] = f"Section {i+1}"
            
            # Skip References section
            if 'references' in section_data['title'].lower():
                if self.debug:
                    print(f"DEBUG: ⏭ Skipping section: {section_data['title']}")
                continue
            
            # Extract section content
            content = self.extract_content_from_section(section)
            if content:
                section_data['content'] = content
                sections.append(section_data)
                if self.debug:
                    print(f"DEBUG: ✓ Extracted section: {section_data['title']}")
            else:
                if self.debug:
                    print(f"DEBUG: ✗ No content found for section: {section_data['title']}")
        
        return sections, article_title

    def extract_section_title_from_element(self, section):
        """Extract section title from section element"""
        # Look for h3 element
        h3_element = section.find('h3')
        if h3_element:
            title = self.clean_text(h3_element.get_text())
            if title:
                return title
        return None

    def extract_content_from_section(self, section):
        """Extract content from a section with comprehensive formatting"""
        content_parts = []
        
        # Find the content container
        content_container = (
            section.find('div', {'data-e2e-test-id': 'section-content-is-shown'}) or
            section.find('div', {'data-e2e-test-id': 'section-content-is-hidden'})
        )
        
        if not content_container:
            return ""
        
        # Find the base styles container
        base_content = content_container.find('div', class_=lambda x: x and 'baseStyles' in x)
        if not base_content:
            base_content = content_container
        
        # Process all direct children
        for child in base_content.children:
            if hasattr(child, 'name') and child.name:
                if child.name == 'h3':
                    # Subsection headers
                    title = self.clean_text(child.get_text())
                    if title:
                        content_parts.append(f"<h3>{title}</h3>")
                
                elif child.name == 'div' and 'table-wrapper' in child.get('class', []):
                    # Tables
                    table = child.find('table')
                    if table:
                        table_content = self.format_table_with_bullets(table)
                        if table_content:
                            content_parts.append(table_content)
                
                elif child.name == 'ul':
                    # Lists
                    list_content = self.process_list(child)
                    if list_content:
                        content_parts.append("<ul>")
                        content_parts.extend(list_content)
                        content_parts.append("</ul>")
                
                elif child.name == 'div' and 'paragraph' in child.get('class', []):
                    # Paragraphs that might contain images
                    images = child.find_all('span', class_='thumbnail__image')
                    for img in images:
                        img_content = self.extract_image_info(img)
                        if img_content:
                            content_parts.append('<div class="image-container">')
                            content_parts.append(img_content)
                            content_parts.append('</div>')
                    
                    # Also extract text content if no images
                    if not images:
                        text_content = self.clean_text(child.get_text())
                        if text_content:
                            content_parts.append(f"<p>{text_content}</p>")
                
                elif child.name == 'div' and any(cls in child.get('class', []) for cls in ['merke', 'cave', 'content-box']):
                    # Content boxes
                    classes = child.get('class', [])
                    content_text = self.clean_text(child.get_text())
                    if content_text:
                        if 'merke' in classes or 'green' in classes:
                            content_parts.append(f'<div class="content-box note">💡 **Note:** {content_text}</div>')
                        elif 'cave' in classes or 'red' in classes:
                            content_parts.append(f'<div class="content-box warning">⚠️ **Warning:** {content_text}</div>')
                        elif 'blue' in classes:
                            content_parts.append(f'<div class="content-box tip">📝 **Tip:** {content_text}</div>')
                        else:
                            content_parts.append(f'<div class="content-box note">💡 **Note:** {content_text}</div>')
                
                elif child.name == 'p':
                    # Direct paragraph elements
                    text_content = self.clean_text(child.get_text())
                    if text_content:
                        content_parts.append(f"<p>{text_content}</p>")
                
                else:
                    # Handle any other content that might contain text
                    processed_content = self.extract_generic_content(child)
                    if processed_content:
                        content_parts.append(processed_content)
        
        return "\n".join(content_parts)
    
    def extract_generic_content(self, element):
        """Extract content from generic elements, handling text and nested structures"""
        if not element or not hasattr(element, 'name'):
            return ""
        
        # Skip if it's a complex container we already handle
        if element.name == 'div':
            classes = element.get('class', [])
            if any(cls in classes for cls in ['table-wrapper', 'paragraph', 'merke', 'cave', 'content-box']):
                return ""
        
        # Check if it contains complex nested elements
        nested_complex = element.find_all(['ul', 'table', 'div'], recursive=False)
        if nested_complex:
            return ""  # Skip complex nested structures
        
        # Extract text content
        text_content = self.clean_text(element.get_text())
        if text_content and len(text_content) > 10:  # Avoid very short fragments
            # If it's a reasonable length and looks like a paragraph, format it as such
            if len(text_content) > 20:
                return f"<p>{text_content}</p>"
        
        return ""
    
    def extract_full_content(self, content_container):
        """Extract all content from the content container with proper formatting"""
        if not content_container:
            return ""
        
        content_parts = []
        
        # Find the base styles container
        base_content = content_container.find('div', class_=lambda x: x and 'baseStyles' in x)
        if not base_content:
            base_content = content_container
        
        # Process all direct children
        for child in base_content.children:
            if hasattr(child, 'name') and child.name:
                if child.name == 'h3':
                    # Subsection headers
                    title = self.clean_text(child.get_text())
                    if title:
                        content_parts.append(f"<h3>{title}</h3>")
                
                elif child.name == 'div' and 'table-wrapper' in child.get('class', []):
                    # Tables
                    table = child.find('table')
                    if table:
                        table_content = self.format_table_with_bullets(table)
                        if table_content:
                            content_parts.append(table_content)
                
                elif child.name == 'ul':
                    # Lists
                    list_content = self.process_list(child)
                    if list_content:
                        content_parts.append("<ul>")
                        content_parts.extend(list_content)
                        content_parts.append("</ul>")
                
                elif child.name == 'div' and 'paragraph' in child.get('class', []):
                    # Paragraphs that might contain images
                    images = child.find_all('span', class_='thumbnail__image')
                    for img in images:
                        img_content = self.extract_image_info(img)
                        if img_content:
                            content_parts.append('<div class="image-container">')
                            content_parts.append(img_content)
                            content_parts.append('</div>')
                    
                    # Also extract text content if no images
                    if not images:
                        text_content = self.clean_text(child.get_text())
                        if text_content:
                            content_parts.append(f"<p>{text_content}</p>")
                
                elif child.name == 'div' and any(cls in child.get('class', []) for cls in ['merke', 'cave', 'content-box']):
                    # Content boxes
                    classes = child.get('class', [])
                    content_text = self.clean_text(child.get_text())
                    if content_text:
                        if 'merke' in classes or 'green' in classes:
                            content_parts.append(f'<div class="content-box note">💡 **Note:** {content_text}</div>')
                        elif 'cave' in classes or 'red' in classes:
                            content_parts.append(f'<div class="content-box warning">⚠️ **Warning:** {content_text}</div>')
                        elif 'blue' in classes:
                            content_parts.append(f'<div class="content-box tip">📝 **Tip:** {content_text}</div>')
                        else:
                            content_parts.append(f'<div class="content-box note">💡 **Note:** {content_text}</div>')
        
        return "\n".join(content_parts)
    

    
    def format_table_with_bullets(self, table_element):
        """Format table exactly like the desired example"""
        if not table_element:
            return ""
        
        rows = []
        
        # Extract headers
        thead = table_element.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = []
                for th in header_row.find_all(['th', 'td']):
                    header_text = self.clean_text(th.get_text())
                    headers.append(header_text if header_text else " ")
                
                if headers:
                    rows.append("| " + " | ".join(headers) + " |")
                    rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        # Extract body rows
        tbody = table_element.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                cells = []
                for td in tr.find_all(['td', 'th']):
                    # Check if cell contains lists
                    top_level_lists = td.find_all('ul', recursive=False)
                    if top_level_lists:
                        # Build bullet list content with line breaks
                        bullet_content = []
                        
                        def process_list_item(li_element, bullet_char="•", indent=""):
                            """Recursively process list items and their nested lists"""
                            # Get the direct text content of this li (excluding nested ul content)
                            li_text_parts = []
                            for content in li_element.contents:
                                if hasattr(content, 'name') and content.name == 'ul':
                                    break  # Stop when we hit nested ul
                                elif hasattr(content, 'get_text'):
                                    text = self.clean_text(content.get_text())
                                    if text:
                                        li_text_parts.append(text)
                                elif isinstance(content, str) and content.strip():
                                    cleaned = self.clean_text(content)
                                    if cleaned:
                                        li_text_parts.append(cleaned)
                            
                            li_text = " ".join(li_text_parts).strip()
                            if li_text:
                                bullet_content.append(f"{indent}{bullet_char} {li_text}")
                            
                            # Process nested lists
                            nested_ul = li_element.find('ul', recursive=False)
                            if nested_ul:
                                for nested_li in nested_ul.find_all('li', recursive=False):
                                    process_list_item(nested_li, "◦", "&nbsp;&nbsp;&nbsp;&nbsp;")
                        
                        # Process all top-level lists
                        for ul in top_level_lists:
                            for li in ul.find_all('li', recursive=False):
                                process_list_item(li)
                        
                        # Join with line breaks and escape pipes
                        cell_text = "<br/>".join(bullet_content).replace('|', '\\|')
                        cells.append(cell_text)
                    else:
                        # No lists, just get text content
                        cell_text = self.clean_text(td.get_text())
                        if cell_text:
                            cell_text = cell_text.replace('\n', ' ').replace('|', '\\|')
                            cells.append(cell_text)
                        else:
                            cells.append("")
                
                if cells:
                    rows.append("| " + " | ".join(cells) + " |")
        
        if rows:
            return "\n<table>\n<thead>\n<tr>\n" + "\n".join(f"<th>{h}</th>" for h in rows[0].split('|')[1:-1]) + "\n</tr>\n</thead>\n<tbody>\n" + "\n".join(f"<tr>\n" + "\n".join(f"<td>{cell}</td>" for cell in row.split('|')[1:-1]) + "\n</tr>" for row in rows[2:]) + "\n</tbody>\n</table>\n"
        else:
            return ""

    def process_list(self, ul_element):
        """Process lists with proper nested formatting"""
        content = []
        
        for li in ul_element.find_all('li', recursive=False):
            # Get the direct text content of this li (excluding nested ul content)
            li_text_parts = []
            for child in li.children:
                if hasattr(child, 'name') and child.name == 'ul':
                    break  # Stop when we hit nested ul
                elif hasattr(child, 'get_text'):
                    text = self.clean_text(child.get_text())
                    if text:
                        li_text_parts.append(text)
                elif isinstance(child, str) and child.strip():
                    cleaned = self.clean_text(child)
                    if cleaned:
                        li_text_parts.append(cleaned)
            
            li_text = " ".join(li_text_parts).strip()
            
            # Start the list item
            if li_text:
                content.append(f"<li>{li_text}")
            else:
                content.append("<li>")
            
            # Process nested lists
            nested_ul = li.find('ul', recursive=False)
            if nested_ul:
                content.append("<ul>")
                nested_content = self.process_list(nested_ul)
                content.extend(nested_content)
                content.append("</ul>")
            
            # Close the list item
            content.append("</li>")
        
        return content

    def extract_image_info(self, img_span):
        """Extract image with proper formatting"""
        if not img_span:
            return ""
        
        # Get the actual img element
        img_element = img_span.find('img')
        if not img_element:
            return ""
        
        # Get image URL from src
        image_url = img_element.get('src', '')
        if not image_url:
            return ""
        
        # Fix relative URLs
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif image_url.startswith('/'):
            image_url = 'https://next.amboss.com' + image_url
        
        # Get title/caption from title attribute or span title
        title = img_element.get('title', '') or img_span.find('span', class_='thumbnail__image__title')
        if hasattr(title, 'get_text'):
            title = title.get_text()
        
        if not title:
            title = "Medical Image"
        
        # Format as centered image with HTML exactly like desired example
        return f'<div style="text-align: center; margin: 20px 0;"><img src="{image_url}" alt="{title}" width="400" style="max-width: 100%; height: auto;"><p><em>{title}</em></p></div>'
    
    def clean_text(self, text):
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        
        # Remove reference numbers like [1], [2], etc.
        text = re.sub(r'\[\d+\](?:\[\d+\])*', '', text)
        
        # Remove unwanted UI elements
        unwanted_strings = ["Maximize table", "Table Quiz", "Collapse", "Notes", "Feedback"]
        for unwanted in unwanted_strings:
            text = text.replace(unwanted, "")
        
        return text.strip()
    
    def format_output(self, sections, output_format='text', article_title=None):
        """
        Format extracted content in the specified format
        
        Args:
            sections (list): List of section dictionaries
            output_format (str): 'text', 'markdown', or 'html'
            article_title (str): Main article title
            
        Returns:
            str: Formatted content
        """
        if output_format == 'text':
            return self._format_text(sections, article_title)
        elif output_format == 'markdown':
            return self._format_markdown(sections, article_title)
        elif output_format == 'html':
            return self._format_html(sections, article_title)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _format_text(self, sections, article_title):
        """Format content as plain text"""
        output = []
        if article_title:
            output.append(f"# {article_title}")
            output.append("")
        
        for i, section in enumerate(sections, 1):
            output.append(f"=== Section {i}: {section['title']} ===")
            output.append(section['content'])
            output.append("")
        
        return '\n'.join(output)
    
    def _format_markdown(self, sections, article_title):
        """Format content as Markdown"""
        output = []
        if article_title:
            output.append(f"# {article_title}")
            output.append("")
        
        for section in sections:
            output.append(f"## {section['title']}")
            output.append("")
            output.append(section['content'])
            output.append("")
        
        return '\n'.join(output)
    
    def _format_html(self, sections, article_title):
        """Format content as HTML with exact CSS from old working version"""
        page_title = article_title or "AMBOSS Content"
        
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'    <title>{page_title}</title>',
            '    <style>',
            '        /* Print-friendly styles */',
            '        @media print {',
            '            body { ',
            '                font-family: \'Times New Roman\', serif;',
            '                font-size: 12pt;',
            '                line-height: 1.4;',
            '                margin: 0.5in;',
            '                color: black;',
            '            }',
            '            ',
            '            /* Section-level styling */',
            '            .section {',
            '                margin-bottom: 20pt;',
            '            }',
            '            ',
            '            /* Main section titles (h2) */',
            '            .section-title {',
            '                font-size: 16pt;',
            '                font-weight: bold;',
            '                margin-top: 24pt;',
            '                margin-bottom: 12pt;',
            '                border-bottom: 2pt solid #333;',
            '                padding-bottom: 6pt;',
            '            }',
            '            ',
            '            /* Subsection titles (h3) */',
            '            h3 {',
            '                font-size: 14pt;',
            '                font-weight: bold;',
            '                margin-top: 18pt;',
            '                margin-bottom: 8pt;',
            '            }',
            '            ',
            '            /* Sub-subsection titles (h4) */',
            '            h4 {',
            '                font-size: 13pt;',
            '                font-weight: bold;',
            '                margin-top: 14pt;',
            '                margin-bottom: 6pt;',
            '            }',
            '            ',
            '            /* Content boxes */',
            '            .content-box {',
            '                border: 1pt solid #666;',
            '                padding: 8pt;',
            '                margin: 12pt 0;',
            '                background-color: #f9f9f9;',
            '            }',
            '            .note { border-left: 4pt solid #4CAF50; }',
            '            .warning { border-left: 4pt solid #f44336; }',
            '            .tip { border-left: 4pt solid #2196F3; }',
            '            .important { border-left: 4pt solid #FF9800; }',
            '            ',
            '            /* Tables */',
            '            table {',
            '                border-collapse: collapse;',
            '                width: 100%;',
            '                margin: 12pt 0;',
            '            }',
            '            th, td {',
            '                border: 1pt solid #333;',
            '                padding: 6pt;',
            '                text-align: left;',
            '                vertical-align: top;',
            '            }',
            '            th {',
            '                background-color: #f0f0f0;',
            '                font-weight: bold;',
            '            }',
            '            ',
            '            /* Images */',
            '            img {',
            '                max-width: 100%;',
            '                height: auto;',
            '                display: block;',
            '                margin: 12pt auto;',
            '            }',
            '            ',
            '            /* Image containers */',
            '            .image-container {',
            '                margin: 12pt 0;',
            '            }',
            '            ',
            '            /* Lists */',
            '            ul, ol {',
            '                margin: 8pt 0;',
            '                padding-left: 20pt;',
            '            }',
            '            ',
            '            /* Individual list items */',
            '            li {',
            '                margin: 4pt 0;',
            '            }',
            '            ',
            '            /* Nested lists */',
            '            ul ul, ol ol, ul ol, ol ul {',
            '                margin: 4pt 0;',
            '            }',
            '            ',
            '            /* Paragraphs */',
            '            p {',
            '                margin: 8pt 0;',
            '            }',
            '        }',
            '',
            '        /* Screen styles */',
            '        @media screen {',
            '            body {',
            '                font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif;',
            '                max-width: 800px;',
            '                margin: 0 auto;',
            '                padding: 20px;',
            '                line-height: 1.6;',
            '                background-color: #fff;',
            '            }',
            '            .section {',
            '                margin-bottom: 30px;',
            '                padding: 20px;',
            '                border-radius: 8px;',
            '                box-shadow: 0 2px 4px rgba(0,0,0,0.1);',
            '            }',
            '            .section-title {',
            '                font-size: 24px;',
            '                font-weight: bold;',
            '                margin-bottom: 15px;',
            '                color: #333;',
            '                border-bottom: 2px solid #007acc;',
            '                padding-bottom: 8px;',
            '            }',
            '            .content-box {',
            '                border-radius: 6px;',
            '                padding: 15px;',
            '                margin: 15px 0;',
            '            }',
            '            .note { ',
            '                background-color: #e8f5e8; ',
            '                border-left: 4px solid #4CAF50; ',
            '            }',
            '            .warning { ',
            '                background-color: #ffeaea; ',
            '                border-left: 4px solid #f44336; ',
            '            }',
            '            .tip { ',
            '                background-color: #e3f2fd; ',
            '                border-left: 4px solid #2196F3; ',
            '            }',
            '            .important { ',
            '                background-color: #fff3e0; ',
            '                border-left: 4px solid #FF9800; ',
            '            }',
            '',
            '            table {',
            '                border-collapse: collapse;',
            '                width: 100%;',
            '                margin: 15px 0;',
            '                box-shadow: 0 1px 3px rgba(0,0,0,0.1);',
            '            }',
            '            th, td {',
            '                border: 1px solid #ddd;',
            '                padding: 12px;',
            '                text-align: left;',
            '            }',
            '            th {',
            '                background-color: #f8f9fa;',
            '                font-weight: 600;',
            '            }',
            '            tr:nth-child(even) {',
            '                background-color: #f8f9fa;',
            '            }',
            '        }',
            '</style>',
            '</head>',
            '<body>'
        ]
        
        # Add main title exactly like the examples
        if article_title:
            html_parts.append('<div class="main-title-container" style="text-align: center; margin-bottom: 30px; border-bottom: 3px solid #007acc; padding-bottom: 15px;">')
            html_parts.append(f'<h1 style="font-size: 28pt; color: #333; margin: 0;">{article_title}</h1>')
            html_parts.append('</div>')
        
        # Add sections exactly like the examples
        for i, section in enumerate(sections, 1):
            html_parts.append(f'<div class="section" id="section-{i}">')
            html_parts.append(f'<h2 class="section-title">{section["title"]}</h2>')
            
            # Content is already in HTML format, no conversion needed
            content_html = section['content']
            html_parts.append(content_html)
            html_parts.append('</div>')
        
        html_parts.extend(['</body>', '</html>'])
        return '\n'.join(html_parts)
    

    
    def generate_filename(self, url, index, output_format, article_title=None):
        """
        Generate a safe filename
        
        Args:
            url (str): Source URL
            index (int): Page index
            output_format (str): Output format
            article_title (str): Article title for filename
            
        Returns:
            str: Safe filename
        """
        if article_title:
            # Use article title as primary filename component
            clean_title = re.sub(r'[^\w\s-]', '', article_title)
            clean_title = re.sub(r'[-\s]+', '_', clean_title)
            clean_title = clean_title.strip('_')[:50]
            page_name = clean_title if clean_title else "article"
        else:
            # Fallback to URL-based name
            page_name = url.split('/')[-1] or url.split('/')[-2]
            page_name = re.sub(r'[^a-zA-Z0-9_-]', '_', page_name)[:50]
        
        # Add extension
        ext_map = {'text': 'txt', 'markdown': 'md', 'html': 'html'}
        ext = ext_map.get(output_format, 'txt')
        
        return f"page_{index:03d}_{page_name}.{ext}"
    
    def scrape_url(self, url, output_format='text'):
        """
        Scrape a single URL or local file
        
        Args:
            url (str): URL to scrape or local file path
            output_format (str): Output format
            
        Returns:
            tuple: (content, article_title)
        """
        try:
            # Handle local files
            if not url.startswith(('http://', 'https://')):
                return self.scrape_local_file(url, output_format)
            
            # Handle web URLs
            if not self.driver:
                if not self.setup_driver():
                    return "Error: Could not setup WebDriver", None
            
            # Login if needed
            if self.username and self.password:
                if not self.login():
                    return "Error: Login failed", None
            
            # Load target page
            self._debug_print(f"Loading page: {url}")
            self.driver.get(url)
            
            # Wait for page load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Expand content
            self.expand_content()
            
            # Extract content
            html_content = self.driver.page_source
            
            if self.debug and self.debug_dir:
                with open(f"{self.debug_dir}/final_page.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
            
            sections, article_title = self.extract_sections(BeautifulSoup(html_content, 'html.parser'))
            
            if not sections:
                return "No content found", None
            
            formatted_content = self.format_output(sections, output_format, article_title)
            return formatted_content, article_title
            
        except Exception as e:
            error_msg = f"Error scraping {url}: {str(e)}"
            self._debug_print(error_msg)
            return error_msg, None
    
    def scrape_local_file(self, filepath, output_format='text'):
        """
        Scrape content from a local HTML file
        
        Args:
            filepath (str): Path to local HTML file
            output_format (str): Output format
            
        Returns:
            tuple: (content, article_title)
        """
        try:
            self._debug_print(f"Reading local file: {filepath}")
            
            # Read local HTML file
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract content directly from HTML
            sections, article_title = self.extract_sections(BeautifulSoup(html_content, 'html.parser'))
            
            if not sections:
                return "No content found in local file", None
            
            formatted_content = self.format_output(sections, output_format, article_title)
            return formatted_content, article_title
            
        except FileNotFoundError:
            error_msg = f"Local file not found: {filepath}"
            self._debug_print(error_msg)
            return error_msg, None
        except Exception as e:
            error_msg = f"Error reading local file {filepath}: {str(e)}"
            self._debug_print(error_msg)
            return error_msg, None
    
    def scrape_url_batch(self, url, output_format='text'):
        """
        Scrape a single URL in batch mode with enhanced debugging
        """
        try:
            # Handle local files
            if not url.startswith(('http://', 'https://')):
                return self.scrape_local_file(url, output_format)
            
            # Handle web URLs (driver should already be setup and logged in)
            if not self.driver:
                return "Error: Browser session not available", None
            
            # Load target page (no login needed - already done)
            self._debug_print(f"Loading page: {url}")
            self.driver.get(url)
            
            # Wait for page load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Add debugging to see what's on the page
            if self.debug:
                self._debug_page_structure()
            
            # Expand content
            self.expand_content()
            
            # Extract content
            html_content = self.driver.page_source
            
            if self.debug and self.debug_dir:
                # Use URL-specific debug filename
                safe_url = re.sub(r'[^a-zA-Z0-9_-]', '_', url.split('/')[-1] or 'page')[:30]
                with open(f"{self.debug_dir}/batch_{safe_url}.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
            
            sections, article_title = self.extract_sections(BeautifulSoup(html_content, 'html.parser'))
            
            if not sections:
                return "No content found", None
            
            formatted_content = self.format_output(sections, output_format, article_title)
            return formatted_content, article_title
            
        except Exception as e:
            error_msg = f"Error scraping {url}: {str(e)}"
            self._debug_print(error_msg)
            return error_msg, None
    
    def _debug_page_structure(self):
        """Debug the page structure to understand what elements are available"""
        try:
            # Check for main content areas
            main_selectors = [
                'article[data-e2e-test-id="learningCardContent"]',
                'article',
                'main',
                '[data-e2e-test-id*="content"]',
                '[data-e2e-test-id*="article"]',
                '[data-e2e-test-id*="learning"]'
            ]
            
            for selector in main_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    self._debug_print(f"Found {len(elements)} elements with selector: {selector}")
                    
                    # If it's the learning card, get more details
                    if 'learningCardContent' in selector and elements:
                        element = elements[0]
                        # Look for sections
                        sections = element.find_elements(By.CSS_SELECTOR, '[data-e2e-test-id="section-with-header"]')
                        self._debug_print(f"Found {len(sections)} sections in learningCardContent")
                        
                        # Look for any content containers
                        content_containers = element.find_elements(By.CSS_SELECTOR, '[data-e2e-test-id*="section-content"]')
                        self._debug_print(f"Found {len(content_containers)} content containers")
            
            # Check for toggle buttons
            toggle_selectors = [
                '[data-e2e-test-id*="toggle"]',
                'button[aria-label*="expand"]',
                'button[aria-label*="collapse"]',
                'button[aria-expanded]'
            ]
            
            for selector in toggle_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    self._debug_print(f"Found {len(elements)} potential toggle elements: {selector}")
            
            # Check page title
            title = self.driver.title
            self._debug_print(f"Page title: {title}")
            
            # Check if we're on the right page
            current_url = self.driver.current_url
            self._debug_print(f"Current URL: {current_url}")
            
        except Exception as e:
            self._debug_print(f"Error debugging page structure: {e}")
    
    def scrape_multiple_urls(self, urls, output_format='text', output_dir=None, delay_range=(1, 3)):
        """
        Scrape multiple URLs with rate limiting and session reuse
        
        Args:
            urls (list): List of URLs to scrape
            output_format (str): Output format
            output_dir (str): Output directory
            delay_range (tuple): Min/max delay between requests
            
        Returns:
            dict: Results for each URL
        """
        results = {}
        successful = 0
        failed = 0
        
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        
        print(f"Starting to scrape {len(urls)} pages...")
        print(f"Delay range: {delay_range[0]}-{delay_range[1]} seconds")
        
        # Setup driver and login once for all URLs
        web_urls = [url for url in urls if url.startswith(('http://', 'https://'))]
        if web_urls:
            print("Setting up browser session...")
            if not self.setup_driver():
                print("ERROR: Could not setup browser session")
                return results
            
            # Login once if credentials provided
            if self.username and self.password:
                print("Logging in...")
                if not self.login():
                    print("ERROR: Login failed")
                    return results
                print("✓ Login successful - will reuse session for all URLs")
        
        print("=" * 50)
        
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Scraping: {url}")
            
            try:
                # Add delay between requests
                if i > 1:
                    delay = random.uniform(delay_range[0], delay_range[1])
                    print(f"  Waiting {delay:.1f} seconds...")
                    time.sleep(delay)
                
                # Scrape the page (skip login since we already did it)
                content, article_title = self.scrape_url_batch(url, output_format)
                results[url] = content
                
                if content and not content.startswith("Error"):
                    successful += 1
                    
                    # Save to file if directory specified
                    if output_dir:
                        filename = self.generate_filename(url, i, output_format, article_title)
                        filepath = os.path.join(output_dir, filename)
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"  ✓ Saved to {filename}")
                    else:
                        print(f"  ✓ Successfully scraped")
                else:
                    failed += 1
                    print(f"  ✗ Failed: {content}")
                
            except Exception as e:
                failed += 1
                error_msg = f"Error: {str(e)}"
                print(f"  ✗ Failed: {error_msg}")
                results[url] = error_msg
        
        print("=" * 50)
        print(f"Scraping completed! Success: {successful}, Failed: {failed}")
        
        return results
    

    

    
    def format_table(self, table):
        """Format table with proper markdown structure"""
        if not table:
            return ""
        
        rows = []
        
        # Process header
        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = []
                for th in header_row.find_all(['th', 'td']):
                    header_text = self.clean_text(th.get_text())
                    headers.append(header_text if header_text else " ")
                
                if headers:
                    rows.append("| " + " | ".join(headers) + " |")
                    rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        # Process body
        tbody = table.find('tbody') or table
        for tr in tbody.find_all('tr'):
            if tr.find_parent('thead'):  # Skip header rows
                continue
                
            cells = []
            for td in tr.find_all(['td', 'th']):
                # Process cell content with proper formatting
                cell_content = self.format_table_cell(td)
                cells.append(cell_content)
            
            if cells:
                rows.append("| " + " | ".join(cells) + " |")
        
        return "\n".join(rows) if rows else ""
    
    def format_table_cell(self, cell):
        """Format table cell content with proper text extraction"""
        cell_parts = []
        
        # Process all elements in the cell
        for element in cell.descendants:
            if hasattr(element, 'name'):
                if element.name == 'br':
                    cell_parts.append('<br/>')
                elif element.name in ['ul', 'ol']:
                    # Handle lists in table cells
                    for li in element.find_all('li', recursive=False):
                        li_text = self.clean_text(li.get_text())
                        if li_text:
                            # Check nesting level
                            parent_lists = len(li.find_parents(['ul', 'ol']))
                            if parent_lists > 1:
                                cell_parts.append(f"&nbsp;&nbsp;&nbsp;&nbsp;◦ {li_text}")
                            else:
                                cell_parts.append(f"• {li_text}")
                elif element.name in ['strong', 'b']:
                    text = self.clean_text(element.get_text())
                    if text and text not in ' '.join(cell_parts):
                        cell_parts.append(f"**{text}**")
                elif element.name in ['em', 'i']:
                    text = self.clean_text(element.get_text())
                    if text and text not in ' '.join(cell_parts):
                        cell_parts.append(f"*{text}*")
            elif isinstance(element, str):
                text = self.clean_text(element)
                if text and text not in ' '.join(cell_parts):
                    cell_parts.append(text)
        
        # Join and clean up
        cell_text = ' '.join(cell_parts).strip()
        
        # Clean up extra spaces and duplicates
        cell_text = re.sub(r'\s+', ' ', cell_text)
        cell_text = cell_text.replace('|', '\\|')  # Escape pipes
        
        return cell_text if cell_text else ""



    def extract_article_title_from_soup(self, soup):
        """Extract article title from BeautifulSoup object"""
        # First try: Extract from HTML title tag
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text().strip()
            # Remove " - AMBOSS" suffix if present
            if title_text.endswith(' - AMBOSS'):
                title_text = title_text[:-9].strip()
            if title_text:
                return title_text
        
        # Second try: Find article header element
        article_header = soup.find(attrs={'data-e2e-test-id': 'articleHeader'})
        if article_header:
            title_element = (
                article_header.find('h1') or 
                article_header.find('h2') or 
                article_header.find(class_=lambda x: x and 'title' in x.lower())
            )
            if title_element:
                return self.clean_text(title_element.get_text())
        
        # Third try: Look for main heading in content
        main_heading = soup.find('h1')
        if main_heading:
            title = self.clean_text(main_heading.get_text())
            if title:
                return title
        
        # Fallback: Generic title
        return "Medical Content"


def read_urls_from_file(filename):
    """Read URLs from a text file"""
    urls = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith(('http://', 'https://')):
                        urls.append(line)
                    else:
                        print(f"Warning: Line {line_num} is not a valid URL: {line}")
        
        print(f"Loaded {len(urls)} URLs from {filename}")
        return urls
    
    except FileNotFoundError:
        print(f"Error: File {filename} not found")
        return []
    except Exception as e:
        print(f"Error reading file {filename}: {e}")
        return []


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='AMBOSS Content Scraper - Extract learning content from AMBOSS articles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape single article
  python amboss_scraper.py "https://next.amboss.com/us/article/abc123"
  
  # Scrape with authentication
  python amboss_scraper.py "https://next.amboss.com/us/article/abc123" \\
    --username your_email@example.com --password your_password
  
  # Batch scraping to markdown files
  python amboss_scraper.py -u urls.txt -f markdown -o output_folder/
  
  # Enable debug output
  python amboss_scraper.py -u urls.txt --debug
        """
    )
    
    # Input options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('url', nargs='?', help='Single URL to scrape')
    group.add_argument('-u', '--urls-file', help='Text file containing URLs (one per line)')
    
    # Output options
    parser.add_argument('-f', '--format', choices=['text', 'markdown', 'html'], 
                       default='text', help='Output format (default: text)')
    parser.add_argument('-o', '--output', 
                       help='Output file (single URL) or directory (multiple URLs)')
    
    # Authentication options
    parser.add_argument('--username', help='AMBOSS email address')
    parser.add_argument('--password', help='AMBOSS password')
    
    # Processing options
    parser.add_argument('--delay', type=float, nargs=2, default=[1, 3], 
                       metavar=('MIN', 'MAX'),
                       help='Delay range between requests in seconds (default: 1 3)')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output and save debug files')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.url is None and args.urls_file is None:
        parser.error('Either provide a URL or use --urls-file')
    
    # Initialize scraper
    scraper = AmbossScraper(
        username=args.username,
        password=args.password,
        debug=args.debug
    )
    
    try:
        if args.urls_file:
            # Batch processing
            urls = read_urls_from_file(args.urls_file)
            if not urls:
                print("No valid URLs found in file.")
                sys.exit(1)
            
            output_dir = args.output or 'amboss_content'
            
            results = scraper.scrape_multiple_urls(
                urls,
                output_format=args.format,
                output_dir=output_dir,
                delay_range=tuple(args.delay)
            )
            
            # Save summary
            summary_file = os.path.join(output_dir, f'_summary_{args.format}.txt')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("AMBOSS Scraping Summary\n")
                f.write("=====================\n")
                f.write(f"Total URLs: {len(urls)}\n")
                f.write(f"Successful: {sum(1 for r in results.values() if not r.startswith('Error'))}\n")
                f.write(f"Failed: {sum(1 for r in results.values() if r.startswith('Error'))}\n")
                f.write(f"Format: {args.format}\n\n")
                
                f.write("Results:\n")
                f.write("-" * 50 + "\n")
                for url, result in results.items():
                    status = "✓" if not result.startswith('Error') else "✗"
                    f.write(f"{status} {url}\n")
            
            print(f"Summary saved to {summary_file}")
        
        else:
            # Single URL processing
            content, article_title = scraper.scrape_url(args.url, args.format)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Content saved to {args.output}")
            else:
                print(content)
    
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)
    finally:
        scraper.cleanup()


if __name__ == "__main__":
    main() 