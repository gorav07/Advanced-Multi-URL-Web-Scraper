Advanced Multi-URL Web Scraper with Enhanced CSV Formatting
A sophisticated Python web scraper designed to extract structured data from multiple URLs and export it in well-organized, readable CSV formats with comprehensive categorization and summary statistics.

🚀 Features
Multi-URL Support: Scrape multiple websites in a single run

Structured Data Extraction: Organized parsing of tables, lists, version information, and content sections

Enhanced CSV Formatting: Clean, readable output with proper column organization

Data Categorization: Automatic separation by data type (tables, lists, versions, sections)

Comprehensive Reporting: Detailed summary statistics and extraction reports

Error Handling: Robust retry mechanisms and error logging

Flexible Configuration: Easy-to-modify settings and URL management

📋 Requirements
bash
pip install httpx beautifulsoup4 selenium webdriver-manager aiofiles
⚙️ Configuration
Adding URLs
Edit the SCRAPING_URLS list in the configuration section:

python
SCRAPING_URLS = [
    'https://example.com/page1',
    'https://example.com/page2',
    'https://example.com/page3',
]
Output Configuration
python
DEFAULT_OUTPUT_FILENAME = "scraped_data"  # Base name for output files
USE_ASYNC_MODE = False  # Set to True for asynchronous scraping
Scraping Options
python
SCRAPING_CONFIG = {
    'extract_tables': True,           # Extract table data
    'extract_lists': True,            # Extract list items
    'extract_sections': True,         # Extract content sections
    'max_content_length': 500 * 1024 * 1024,  # Maximum content size
    'timeout': 120,                   # Request timeout in seconds
    'retry_attempts': 5,              # Number of retry attempts
}
🛠️ Usage
Basic Usage
python
from scraper import run_formatted_scraper

# Scrape with default URLs and settings
result = run_formatted_scraper()

# Scrape custom URLs
urls = ['https://example.com/page1', 'https://example.com/page2']
result = run_formatted_scraper(urls=urls, output_name="my_data")
Advanced Usage
python
from scraper import FormattedScraper, ScraperConfig

# Custom configuration
config = ScraperConfig()
config.timeout = 60
config.retry_attempts = 3

# Initialize scraper
scraper = FormattedScraper(config)

# Run scraping
urls = ['https://example.com/page1', 'https://example.com/page2']
result = scraper.run_scraping(urls, "custom_output")
📊 Output Files
The scraper generates multiple organized CSV files:

{output_name}.csv - Main combined data file

{output_name}_table_data.csv - Extracted table data only

{output_name}_version_info.csv - Software version information

{output_name}_list_item.csv - List items and bullet points

{output_name}_section_content.csv - Content sections with headings

{output_name}_summary.csv - Comprehensive scraping summary report

🎯 Data Extraction Types
1. Table Data
Extracts structured table content

Preserves column headers and row data

Handles complex table structures

2. Version Information
Automatically detects version numbers (e.g., 1.2.3, v2.1.0)

Identifies release dates and version patterns

Provides context for version references

3. List Items
Extracts ordered and unordered lists

Preserves list hierarchy and structure

Captures list context and item indexes

4. Content Sections
Extracts content organized by headings

Preserves hierarchical structure (H1-H6)

Combines related content pieces

📈 Output Structure
Each record includes:

record_id - Unique identifier for each data point

data_type - Category of data (table_data, version_info, etc.)

source_url - Original URL source

domain - Website domain

extraction_timestamp - When data was extracted

Type-specific fields (columns, version numbers, content, etc.)

🔧 Customization
Adding New Data Extractors
Extend the StructuredDataParser class:

python
class CustomDataParser(StructuredDataParser):
    def _extract_custom_data(self) -> List[Dict[str, Any]]:
        # Your custom extraction logic
        custom_data = []
        # ... extraction code
        return custom_data
    
    def parse_structured_data(self) -> List[Dict[str, Any]]:
        data = super().parse_structured_data()
        custom_data = self._extract_custom_data()
        data.extend(custom_data)
        return data
Custom CSV Formatting
Modify the FormattedCSVExporter class:

python
class CustomExporter(FormattedCSVExporter):
    def _organize_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Your custom organization logic
        organized_data = []
        # ... organization code
        return organized_data
🐛 Error Handling
The scraper includes comprehensive error handling:

Retry Mechanism: Automatic retries for failed requests

Timeout Handling: Configurable timeouts for slow responses

Content Validation: Checks for minimum content quality

Logging: Detailed logging for debugging and monitoring

📝 Logging
Logs are saved to scraper.log with:

Timestamped entries

Success/failure indicators

Detailed error information

Extraction statistics

⚠️ Important Notes
Respect robots.txt: Always check website terms of service

Rate Limiting: Add delays between requests for large-scale scraping

Legal Compliance: Ensure compliance with local laws and website policies

Resource Usage: Monitor memory usage for large scraping jobs

🎪 Example Output
Summary Report Example:
text
report_type,total_urls,successful_urls,failed_urls,total_records,success_rate
OVERALL_SUMMARY,3,3,0,156,100.0%
URL_REPORT,https://example.com,45,success,example.com
DATA_TYPE_SUMMARY,table_data,67,42.9%
DATA_TYPE_SUMMARY,version_info,23,14.7%
📞 Support
For issues and feature requests, please check the logging output and ensure all dependencies are properly installed.

📄 License
This project is for educational and legitimate web scraping purposes. Users are responsible for complying with website terms of service and applicable laws.
