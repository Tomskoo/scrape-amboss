# AMBOSS Content Scraper

A production-ready web scraper for extracting rich medical content from AMBOSS articles with comprehensive formatting support.

*To my love, Allyson. I'd program anything for you.* 💕

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Scrape a single article
python amboss_scraper.py "https://next.amboss.com/us/article/abc123"

# Scrape with authentication
python amboss_scraper.py "https://next.amboss.com/us/article/abc123" \
  --username your_email@example.com --password your_password

# Scrape from local HTML file (content must be fully expanded)
python amboss_scraper.py saved_article.html -f markdown

# Batch scraping to markdown
python amboss_scraper.py -u example_urls.txt -f markdown -o output/
```

## Features

✅ **Rich Content Extraction**: Tables, images, content boxes, and nested lists  
✅ **Selenium-based**: Automatically expands collapsible content  
✅ **Authentication**: Seamless AMBOSS login support  
✅ **Multiple formats**: Text, Markdown, and HTML output with professional styling  
✅ **Local HTML support**: Process saved HTML files (requires expanded content)  
✅ **Batch processing**: Process multiple URLs with rate limiting and session reuse  
✅ **Smart naming**: Uses article titles for filenames  
✅ **Debug mode**: Optional detailed logging for troubleshooting  

## Content Extraction Capabilities

The scraper provides comprehensive extraction of medical content including:

### Rich HTML Tables
- Preserves complex nested bullet points and formatting
- Maintains proper table structure with headers and data cells
- Handles medical terminology and dosage information

### Images and Figures
- Extracts medical images with proper captions
- Maintains responsive sizing and center alignment
- Preserves image URLs and alt text

### Content Boxes
- Extracts color-coded medical notes, warnings, and tips
- Preserves icons and formatting (💡 Notes, ⚠️ Warnings, 📝 Tips)
- Maintains proper styling in HTML output

### Nested Lists
- Handles multi-level bullet points and numbered lists
- Preserves indentation and list hierarchy
- Maintains medical content structure

## Requirements

- Python 3.7+
- Chrome/Chromium browser
- ChromeDriver (auto-managed by Selenium 4.x)

## Input Options

### Web URLs
Process live AMBOSS articles directly from URLs. The scraper automatically:
- Handles authentication if credentials provided
- Expands all collapsible content sections
- Extracts the fully expanded content

### Local HTML Files
Process saved HTML files from your browser:
```bash
python amboss_scraper.py saved_article.html -f markdown
```

**⚠️ Important**: For local HTML files to work correctly, you must manually expand all content sections in your browser before saving the HTML file. The scraper cannot expand collapsed sections in static HTML files.

## Files

- `amboss_scraper.py` - Main scraper script
- `requirements.txt` - Python dependencies
- `example_urls.txt` - Example URL file template
- `LICENSE` - MIT License file

---

## Detailed Documentation

### Installation Guide

#### 1. Python Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Browser Requirements
The scraper uses Chrome in headless mode:
- **Ubuntu/Debian**: `sudo apt install chromium-browser`
- **macOS**: `brew install --cask google-chrome`
- **Windows**: Download from [Google Chrome](https://www.google.com/chrome/)

#### 3. ChromeDriver Setup
- **Automatic**: ChromeDriver should be automatically managed by Selenium 4.x
- **Manual**: Download from [ChromeDriver Downloads](https://chromedriver.chromium.org/) and add to PATH

### Usage Examples

#### Basic Usage
```bash
# Scrape single article to console (text format)
python amboss_scraper.py "https://next.amboss.com/us/article/abc123"

# Save to specific file
python amboss_scraper.py "https://next.amboss.com/us/article/abc123" -o article.txt

# Output as markdown
python amboss_scraper.py "https://next.amboss.com/us/article/abc123" -f markdown -o article.md

# Output as HTML
python amboss_scraper.py "https://next.amboss.com/us/article/abc123" -f html -o article.html
```

#### Batch Processing
```bash
# Process multiple URLs from file
python amboss_scraper.py -u example_urls.txt -o scraped_content/

# With authentication and custom delay
python amboss_scraper.py -u example_urls.txt \
  --username your_email@example.com \
  --password your_password \
  --delay 2 5 \
  -f markdown \
  -o medical_articles/

# Enable debug mode for troubleshooting
python amboss_scraper.py -u example_urls.txt --debug
```

### Command Line Options

#### Required (choose one)
- `URL` - Single URL to scrape
- `-u, --urls-file FILE` - Text file containing URLs (one per line)

#### Optional
- `-f, --format {text,markdown,html}` - Output format (default: text)
- `-o, --output PATH` - Output file (single URL) or directory (multiple URLs)
- `--username EMAIL` - AMBOSS email address for authentication
- `--password PASSWORD` - AMBOSS password for authentication
- `--delay MIN MAX` - Delay range between requests in seconds (default: 1 3)
- `--debug` - Enable debug output and save debug files

### Authentication

#### Providing Credentials
```bash
# Command line (not recommended for security)
python amboss_scraper.py URL --username your_email@example.com --password your_password

# Environment variables (recommended)
export AMBOSS_USERNAME="your_email@example.com"
export AMBOSS_PASSWORD="your_password"
python amboss_scraper.py URL --username "$AMBOSS_USERNAME" --password "$AMBOSS_PASSWORD"
```

#### Security Notes
- Never hardcode credentials in scripts
- Use environment variables or secure credential management
- Consider using a dedicated account for scraping

### Output Formats

#### Text Format
- Plain text with section headers
- Simple formatting preserved
- Good for basic content extraction

#### Markdown Format
- Structured markdown with headers
- Lists and tables in markdown syntax
- Compatible with documentation systems

#### HTML Format
- Complete HTML document with CSS
- Print-friendly styling
- Professional formatting for presentations

### File Naming

The scraper automatically generates descriptive filenames:
- **With Article Title**: `page_001_Cyanotic_congenital_heart_defects.md`
- **Without Title**: `page_001_article_id.md`
- **Format**: `page_XXX_title.extension`

### Debug Mode

Enable debug mode for troubleshooting:
```bash
python amboss_scraper.py URL --debug
```

Debug mode creates a `debug_amboss/` directory with:
- `login_page.html` - Login page HTML
- `expanded_content.html` - Page after content expansion
- `final_page.html` - Final page HTML before extraction
- Console output with detailed processing steps

### Error Handling

#### Common Issues

**"Selenium not available"**
- Install selenium: `pip install selenium`

**"Could not setup WebDriver"**
- Install Chrome/Chromium browser
- Check ChromeDriver installation
- Verify ChromeDriver is in PATH

**"Login failed"**
- Verify AMBOSS credentials
- Check internet connection
- Try with debug mode: `--debug`

**"No content found"**
- URL may not contain learningCardContent article
- Try with authentication for premium content
- Enable debug mode to inspect page structure

#### Rate Limiting
- Default delay: 1-3 seconds between requests
- Adjust with `--delay MIN MAX` option
- Respect AMBOSS terms of service

### Troubleshooting

1. **Enable Debug Mode**: Use `--debug` flag for detailed logs
2. **Check Prerequisites**: Ensure Chrome and ChromeDriver are installed
3. **Verify URLs**: Ensure URLs point to valid AMBOSS articles
4. **Authentication**: Try both with and without credentials
5. **Network**: Check internet connection and firewall settings

### Legal and Ethical Use

- **Respect Terms of Service**: Use in accordance with AMBOSS terms
- **Rate Limiting**: Don't overwhelm servers with rapid requests
- **Personal Use**: Intended for personal learning and research
- **Copyright**: Respect intellectual property rights
- **Attribution**: Consider citing AMBOSS as the source

### Support

For issues and questions:
1. Check the troubleshooting section above
2. Run with `--debug` flag to gather diagnostic information
3. Review the debug files created in `debug_amboss/` directory

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Legal

This tool is for educational and research purposes. Users are responsible for complying with AMBOSS terms of service and applicable laws. 