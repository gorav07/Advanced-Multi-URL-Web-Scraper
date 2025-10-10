"""
Advanced Multi-URL Web Scraper with Enhanced CSV Formatting
Better data organization and CSV structure for readable output.

Features:
1. Structured CSV with clear columns
2. Data categorization by source type
3. Clean, readable output format
4. Better data filtering and organization
5. Summary statistics in CSV
"""

import csv
import json
import logging
import asyncio
import aiofiles
import sys
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
from urllib.parse import urlparse
import re
import time

import httpx
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ==============================================================================
# 0. CONFIGURATION - SINGLE PLACE TO ADD/MODIFY URLs
# ==============================================================================

# ADD YOUR URLs HERE - This is the only place you need to modify for URLs
SCRAPING_URLS = [
    'https://www.dbf2002.com/news.html',
    
    
]

# Output configuration
DEFAULT_OUTPUT_FILENAME = "software_versions_data"
USE_ASYNC_MODE = False

# Enhanced scraping configuration
SCRAPING_CONFIG = {
    'extract_tables': True,
    'extract_lists': True,
    'extract_definition_lists': True,
    'extract_sections': True,
    'extract_paragraphs': True,
    'max_content_length': 500 * 1024 * 1024,
    'timeout': 120,
    'retry_attempts': 5,
    'retry_delay': 3,
    'min_content_length': 5,  # Minimum characters for valid content
}

# ==============================================================================
# 1. CUSTOM EXCEPTIONS & CONFIGURATION
# ==============================================================================

class ScraperException(Exception):
    pass

class FetchException(ScraperException):
    pass

class ParseException(ScraperException):
    pass

class ExportException(ScraperException):
    pass

class ScraperConfig:
    def __init__(self):
        self.timeout = SCRAPING_CONFIG['timeout']
        self.retry_attempts = SCRAPING_CONFIG['retry_attempts']
        self.retry_delay = SCRAPING_CONFIG['retry_delay']
        self.max_connections = 10
        self.chrome_options = [
            "--headless", "--no-sandbox", "--disable-dev-shm-usage",
            "--disable-gpu", "--window-size=1920,1080",
            "--disable-blink-features=AutomationControlled",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ]
        self.valid_domains = []
        self.max_content_size = SCRAPING_CONFIG['max_content_length']

# ==============================================================================
# 2. ENHANCED LOGGING SYSTEM
# ==============================================================================

class ScraperLogger:
    def __init__(self, name: str = "WebScraper", log_file: str = "scraper.log"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str): self.logger.info(message)
    def error(self, message: str, exc_info: bool = True): self.logger.error(message, exc_info=exc_info)
    def warning(self, message: str): self.logger.warning(message)
    def debug(self, message: str): self.logger.debug(message)
    def success(self, message: str): self.logger.info(f"✅ {message}")
    def failure(self, message: str): self.logger.error(f"❌ {message}")

# ==============================================================================
# 3. ENHANCED DATA PARSER WITH BETTER STRUCTURE
# ==============================================================================

class StructuredDataParser:
    """
    Enhanced parser that creates well-structured, organized data for CSV.
    """
    
    def __init__(self, html_content: str, url: str, logger: ScraperLogger = None):
        if not html_content:
            raise ValueError("HTML content cannot be empty.")
        
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.url = url
        self.domain = urlparse(url).netloc
        self.logger = logger or ScraperLogger()
        self.extraction_stats = {
            'tables': 0, 'lists': 0, 'definitions': 0, 'sections': 0, 'versions': 0
        }

    def _clean_text(self, text: str) -> str:
        """Enhanced text cleaning for better readability."""
        if not text:
            return ""
        cleaned = re.sub(r'\s+', ' ', text.strip())
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        # Remove common unwanted patterns
        cleaned = re.sub(r'\[\d+\]', '', cleaned)  # Remove citation markers [1], [2], etc.
        cleaned = re.sub(r'\s*\.\s*', '. ', cleaned)  # Fix spacing around periods
        return cleaned.strip()

    def _is_valid_content(self, text: str, min_length: int = None) -> bool:
        """Check if content meets minimum quality standards."""
        if min_length is None:
            min_length = SCRAPING_CONFIG['min_content_length']
        
        if not text or len(text) < min_length:
            return False
        
        # Check if text contains meaningful content (not just symbols or numbers)
        word_count = len(re.findall(r'\b[a-zA-Z]{2,}\b', text))
        return word_count >= 1

    def _extract_structured_tables(self) -> List[Dict[str, Any]]:
        """Extract well-structured table data with clear columns."""
        table_data = []
        tables = self.soup.find_all('table')
        
        for table_idx, table in enumerate(tables):
            try:
                # Get table context
                caption = table.find('caption')
                table_context = self._clean_text(caption.get_text()) if caption else f"Table_{table_idx + 1}"
                
                # Extract headers
                headers = []
                header_row = table.find('thead')
                if header_row:
                    headers = [self._clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]
                
                if not headers:
                    first_row = table.find('tr')
                    if first_row:
                        headers = [self._clean_text(cell.get_text()) for cell in first_row.find_all(['th', 'td'])]
                
                # Use meaningful default headers
                if not headers:
                    max_cols = max(len(row.find_all(['td', 'th'])) for row in table.find_all('tr')) if table.find_all('tr') else 0
                    headers = [f'Column_{i+1}' for i in range(max_cols)]
                
                # Extract data rows
                rows = table.find('tbody') or table
                data_rows = rows.find_all('tr')
                
                for row_idx, row in enumerate(data_rows):
                    # Skip if this is likely a header row
                    if row == first_row:
                        continue
                    
                    cells = row.find_all(['td', 'th'])
                    if not cells:
                        continue
                    
                    # Create structured record
                    record = {
                        'data_type': 'table_data',
                        'source_url': self.url,
                        'table_context': table_context,
                        'row_index': row_idx,
                        'domain': self.domain,
                    }
                    
                    # Add cell data with meaningful column names
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            col_name = headers[i] or f'column_{i+1}'
                        else:
                            col_name = f'column_{i+1}'
                        
                        cell_text = self._clean_text(cell.get_text())
                        if self._is_valid_content(cell_text):
                            record[col_name] = cell_text
                    
                    # Only add records with meaningful data
                    data_fields = {k: v for k, v in record.items() if k not in ['data_type', 'source_url', 'table_context', 'row_index', 'domain']}
                    if any(data_fields.values()):
                        table_data.append(record)
                        
            except Exception as e:
                self.logger.warning(f"Error parsing table {table_idx}: {e}")
                continue
        
        self.extraction_stats['tables'] = len(table_data)
        self.logger.info(f"Extracted {len(table_data)} structured table records")
        return table_data

    def _extract_version_information(self) -> List[Dict[str, Any]]:
        """Specifically look for version numbers and release information."""
        version_data = []
        
        # Common version patterns
        version_patterns = [
            r'\b\d+\.\d+\.\d+\b',  # 1.2.3
            r'\b\d+\.\d+\b',        # 1.2
            r'\bv?\d+\.\d+\.\d+[a-zA-Z]?\b',  # v1.2.3 or 1.2.3a
            r'\b\d{4}-\d{2}-\d{2}\b',  # 2024-01-01
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
        ]
        
        # Look for version information in various elements
        elements_to_check = [
            ('table', self.soup.find_all('table')),
            ('list', self.soup.find_all(['ul', 'ol'])),
            ('heading', self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
            ('paragraph', self.soup.find_all('p')),
        ]
        
        for elem_type, elements in elements_to_check:
            for elem_idx, elem in enumerate(elements):
                try:
                    text = self._clean_text(elem.get_text())
                    if not self._is_valid_content(text, min_length=20):
                        continue
                    
                    # Look for version patterns
                    for pattern in version_patterns:
                        versions = re.findall(pattern, text)
                        if versions:
                            # Get context
                            context = "Unknown"
                            if elem_type == 'table':
                                context = f"Table_{elem_idx + 1}"
                            elif elem_type == 'list':
                                context = f"List_{elem_idx + 1}"
                            elif elem_type == 'heading':
                                context = f"Heading: {text[:50]}..."
                            else:
                                context = f"Paragraph_{elem_idx + 1}"
                            
                            for version in versions[:3]:  # Limit to first 3 versions per element
                                version_data.append({
                                    'data_type': 'version_info',
                                    'source_url': self.url,
                                    'domain': self.domain,
                                    'version_number': version,
                                    'context': context,
                                    'element_type': elem_type,
                                    'full_text': text[:200] + '...' if len(text) > 200 else text,
                                })
                            
                except Exception as e:
                    continue
        
        self.extraction_stats['versions'] = len(version_data)
        self.logger.info(f"Found {len(version_data)} version references")
        return version_data

    def _extract_structured_lists(self) -> List[Dict[str, Any]]:
        """Extract list data in structured format."""
        list_data = []
        lists = self.soup.find_all(['ol', 'ul'])
        
        for list_idx, list_elem in enumerate(lists):
            try:
                # Get list context
                context = "List"
                prev_elem = list_elem.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'])
                if prev_elem:
                    context = self._clean_text(prev_elem.get_text())[:100]
                
                items = list_elem.find_all('li')
                for item_idx, item in enumerate(items):
                    text = self._clean_text(item.get_text())
                    if self._is_valid_content(text):
                        list_data.append({
                            'data_type': 'list_item',
                            'source_url': self.url,
                            'domain': self.domain,
                            'list_context': context,
                            'item_index': item_idx,
                            'content': text,
                            'list_type': list_elem.name,
                            'total_items': len(items),
                        })
                        
            except Exception as e:
                self.logger.warning(f"Error parsing list {list_idx}: {e}")
                continue
        
        self.extraction_stats['lists'] = len(list_data)
        self.logger.info(f"Extracted {len(list_data)} list items")
        return list_data

    def _extract_content_sections(self) -> List[Dict[str, Any]]:
        """Extract structured content from page sections."""
        section_data = []
        headings = self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for heading in headings:
            try:
                heading_text = self._clean_text(heading.get_text())
                if not heading_text:
                    continue
                
                # Extract content under this heading
                content_parts = []
                next_elem = heading.next_sibling
                content_limit = 5  # Limit number of elements to collect
                
                while next_elem and content_limit > 0:
                    if hasattr(next_elem, 'get_text'):
                        text = self._clean_text(next_elem.get_text())
                        if self._is_valid_content(text, min_length=30):
                            content_parts.append(text)
                            content_limit -= 1
                    
                    next_elem = next_elem.next_sibling
                    if next_elem and next_elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        break
                
                if content_parts:
                    section_data.append({
                        'data_type': 'section_content',
                        'source_url': self.url,
                        'domain': self.domain,
                        'heading': heading_text,
                        'heading_level': heading.name,
                        'content': ' | '.join(content_parts[:3]),  # Combine first 3 content pieces
                        'content_pieces': len(content_parts),
                    })
                    
            except Exception as e:
                self.logger.warning(f"Error extracting section: {e}")
                continue
        
        self.extraction_stats['sections'] = len(section_data)
        self.logger.info(f"Extracted {len(section_data)} content sections")
        return section_data

    def parse_structured_data(self) -> List[Dict[str, Any]]:
        """Main method that returns well-structured, organized data."""
        all_data = []
        
        self.logger.info("Starting structured data extraction...")
        
        # Extract different types of data
        if SCRAPING_CONFIG['extract_tables']:
            table_data = self._extract_structured_tables()
            all_data.extend(table_data)
        
        if SCRAPING_CONFIG['extract_lists']:
            list_data = self._extract_structured_lists()
            all_data.extend(list_data)
        
        if SCRAPING_CONFIG['extract_sections']:
            section_data = self._extract_content_sections()
            all_data.extend(section_data)
        
        # Always look for version information
        version_data = self._extract_version_information()
        all_data.extend(version_data)
        
        # Add metadata and timestamp
        timestamp = datetime.now().isoformat()
        for record in all_data:
            record['extraction_timestamp'] = timestamp
            record['record_id'] = f"{hash(self.url) % 10000:04d}_{len(all_data)}"
        
        self.logger.success(f"Structured extraction completed: {len(all_data)} meaningful records")
        return all_data

    def get_extraction_report(self) -> Dict[str, Any]:
        """Get extraction statistics report."""
        return self.extraction_stats

# ==============================================================================
# 4. ENHANCED CSV EXPORTER WITH BETTER FORMATTING
# ==============================================================================

class FormattedCSVExporter:
    """
    Creates well-formatted, readable CSV files with proper organization.
    """
    
    def __init__(self, data: List[Dict[str, Any]], logger: ScraperLogger = None):
        self.original_data = data
        self.logger = logger or ScraperLogger()
        self.data = self._organize_data(data)
    
    def _organize_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Organize data by type and ensure consistent structure."""
        organized_data = []
        
        for record in data:
            # Create a standardized record format
            standardized = {
                'record_id': record.get('record_id', ''),
                'data_type': record.get('data_type', 'unknown'),
                'source_url': record.get('source_url', ''),
                'domain': record.get('domain', ''),
                'extraction_timestamp': record.get('extraction_timestamp', ''),
            }
            
            # Add type-specific fields in a consistent way
            data_type = record.get('data_type', '')
            
            if data_type == 'table_data':
                standardized.update({
                    'table_context': record.get('table_context', ''),
                    'row_index': record.get('row_index', ''),
                    'column_1': record.get(record.get('column_1', 'column_1'), ''),
                    'column_2': record.get(record.get('column_2', 'column_2'), ''),
                    'column_3': record.get(record.get('column_3', 'column_3'), ''),
                    'column_4': record.get(record.get('column_4', 'column_4'), ''),
                    'additional_data': str({k: v for k, v in record.items() 
                                          if k not in standardized and k not in ['table_context', 'row_index']})
                })
            
            elif data_type == 'version_info':
                standardized.update({
                    'version_number': record.get('version_number', ''),
                    'context': record.get('context', ''),
                    'element_type': record.get('element_type', ''),
                    'full_text': record.get('full_text', '')[:100],  # Truncate long text
                })
            
            elif data_type == 'list_item':
                standardized.update({
                    'list_context': record.get('list_context', ''),
                    'item_index': record.get('item_index', ''),
                    'content': record.get('content', ''),
                    'list_type': record.get('list_type', ''),
                    'total_items': record.get('total_items', ''),
                })
            
            elif data_type == 'section_content':
                standardized.update({
                    'heading': record.get('heading', ''),
                    'heading_level': record.get('heading_level', ''),
                    'content': record.get('content', ''),
                    'content_pieces': record.get('content_pieces', ''),
                })
            
            else:
                # For unknown types, include all fields in a structured way
                content_fields = {k: v for k, v in record.items() 
                                if k not in standardized and k != 'data_type'}
                standardized['content'] = str(content_fields) if content_fields else ''
            
            organized_data.append(standardized)
        
        return organized_data
    
    def export_formatted_csv(self, filename: str):
        """Export data to a well-formatted CSV file."""
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        if not self.data:
            self.logger.warning("No data to export")
            return
        
        try:
            # Define column order for better readability
            base_columns = ['record_id', 'data_type', 'source_url', 'domain', 'extraction_timestamp']
            type_specific_columns = {
                'table_data': ['table_context', 'row_index', 'column_1', 'column_2', 'column_3', 'column_4', 'additional_data'],
                'version_info': ['version_number', 'context', 'element_type', 'full_text'],
                'list_item': ['list_context', 'item_index', 'content', 'list_type', 'total_items'],
                'section_content': ['heading', 'heading_level', 'content', 'content_pieces'],
            }
            
            # Get all possible columns
            all_columns = set(base_columns)
            for columns in type_specific_columns.values():
                all_columns.update(columns)
            
            # Write to CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=sorted(all_columns))
                writer.writeheader()
                
                for record in self.data:
                    # Ensure all columns are present in each record
                    full_record = {col: record.get(col, '') for col in sorted(all_columns)}
                    writer.writerow(full_record)
            
            self.logger.success(f"Formatted CSV exported: {filename}")
            self.logger.info(f"Total records: {len(self.data)}")
            self.logger.info(f"Columns: {len(all_columns)}")
            
        except Exception as e:
            raise ExportException(f"Error exporting CSV: {e}")
    
    def export_by_data_type(self, base_filename: str):
        """Export separate CSV files for each data type."""
        data_by_type = {}
        
        for record in self.data:
            data_type = record.get('data_type', 'unknown')
            if data_type not in data_by_type:
                data_by_type[data_type] = []
            data_by_type[data_type].append(record)
        
        for data_type, records in data_by_type.items():
            # Clean filename
            clean_type = data_type.replace(' ', '_').lower()
            filename = f"{base_filename}_{clean_type}.csv"
            
            if records:
                exporter = FormattedCSVExporter(records, self.logger)
                exporter.export_formatted_csv(filename)
                self.logger.info(f"Exported {len(records)} {data_type} records to {filename}")

# ==============================================================================
# 5. ENHANCED MAIN SCRAPER WITH BETTER OUTPUT
# ==============================================================================

class FormattedScraper:
    """Main scraper that produces well-formatted, organized output."""
    
    def __init__(self, config: ScraperConfig = None):
        self.config = config or ScraperConfig()
        self.logger = ScraperLogger("FormattedScraper")
        self.stats = {
            'start_time': datetime.now(),
            'urls_processed': 0,
            'urls_successful': 0,
            'urls_failed': 0,
            'total_records': 0,
        }

    def scrape_url(self, url: str) -> List[Dict[str, Any]]:
        """Scrape a single URL and return structured data."""
        try:
            self.logger.info(f"🔄 Scraping: {url}")
            
            # Fetch content
            scraper = StaticScraper(url, self.config, self.logger)
            content = scraper.scrape()
            
            # Parse with structured parser
            parser = StructuredDataParser(content, url, self.logger)
            data = parser.parse_structured_data()
            
            self.stats['urls_processed'] += 1
            self.stats['urls_successful'] += 1
            self.stats['total_records'] += len(data)
            
            self.logger.success(f"✅ Extracted {len(data)} meaningful records from {url}")
            
            return data
            
        except Exception as e:
            self.stats['urls_processed'] += 1
            self.stats['urls_failed'] += 1
            self.logger.failure(f"❌ Failed to scrape {url}: {e}")
            return []

    def run_scraping(self, urls: List[str], output_base: str) -> Dict[str, Any]:
        """Run scraping on all URLs and export formatted results."""
        self.logger.info(f"🚀 Starting formatted scraping for {len(urls)} URLs")
        
        all_data = []
        url_reports = []
        
        for url in urls:
            data = self.scrape_url(url)
            all_data.extend(data)
            
            url_reports.append({
                'url': url,
                'records_extracted': len(data),
                'status': 'success' if data else 'failed'
            })
        
        # Export formatted results
        if all_data:
            self._export_results(all_data, output_base, url_reports)
        else:
            self.logger.warning("No data collected from any URL")
        
        return {
            'data': all_data,
            'url_reports': url_reports,
            'stats': self.stats.copy()
        }
    
    def _export_results(self, data: List[Dict[str, Any]], output_base: str, url_reports: List[Dict]):
        """Export results in multiple formatted ways."""
        # Main combined CSV
        main_exporter = FormattedCSVExporter(data, self.logger)
        main_exporter.export_formatted_csv(output_base)
        
        # Separate CSVs by data type
        main_exporter.export_by_data_type(output_base)
        
        # Create a summary report
        self._create_summary_report(output_base, url_reports, data)
    
    def _create_summary_report(self, output_base: str, url_reports: List[Dict], data: List[Dict]):
        """Create a summary CSV with scraping statistics."""
        summary_data = []
        
        # Overall summary
        summary_data.append({
            'report_type': 'OVERALL_SUMMARY',
            'total_urls': len(url_reports),
            'successful_urls': self.stats['urls_successful'],
            'failed_urls': self.stats['urls_failed'],
            'total_records': self.stats['total_records'],
            'success_rate': f"{(self.stats['urls_successful'] / len(url_reports) * 100):.1f}%",
            'scraping_duration': f"{(datetime.now() - self.stats['start_time']).total_seconds():.1f}s",
        })
        
        # Per-URL summary
        for report in url_reports:
            summary_data.append({
                'report_type': 'URL_REPORT',
                'url': report['url'],
                'records_extracted': report['records_extracted'],
                'status': report['status'],
                'domain': urlparse(report['url']).netloc,
            })
        
        # Data type summary
        data_by_type = {}
        for record in data:
            data_type = record.get('data_type', 'unknown')
            data_by_type[data_type] = data_by_type.get(data_type, 0) + 1
        
        for data_type, count in data_by_type.items():
            summary_data.append({
                'report_type': 'DATA_TYPE_SUMMARY',
                'data_type': data_type,
                'record_count': count,
                'percentage': f"{(count / len(data) * 100):.1f}%",
            })
        
        # Export summary
        summary_filename = f"{output_base}_summary.csv"
        try:
            with open(summary_filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['report_type', 'total_urls', 'successful_urls', 'failed_urls', 
                            'total_records', 'success_rate', 'scraping_duration', 'url',
                            'records_extracted', 'status', 'domain', 'data_type', 'record_count', 'percentage']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for record in summary_data:
                    writer.writerow(record)
            
            self.logger.success(f"Summary report exported: {summary_filename}")
            
        except Exception as e:
            self.logger.error(f"Error exporting summary: {e}")

# ==============================================================================
# 6. MAIN EXECUTION FUNCTION
# ==============================================================================

def run_formatted_scraper(urls: List[str] = None, output_name: str = None):
    """
    Run the formatted scraper with well-structured output.
    
    Args:
        urls: List of URLs to scrape
        output_name: Base name for output files
    """
    if urls is None:
        urls = SCRAPING_URLS
    if output_name is None:
        output_name = DEFAULT_OUTPUT_FILENAME
    
    print("=" * 70)
    print("📊 FORMATTED WEB SCRAPER - WELL-STRUCTURED CSV OUTPUT")
    print("=" * 70)
    print(f"📋 URLs to scrape: {len(urls)}")
    print(f"💾 Output base: {output_name}")
    print()
    
    # Print URL list
    print("🌐 Target URLs:")
    for i, url in enumerate(urls, 1):
        print(f"   {i:2d}. {url}")
    print()
    
    # Run scraper
    scraper = FormattedScraper()
    result = scraper.run_scraping(urls, output_name)
    
    # Print final summary
    print("\n" + "=" * 70)
    print("🎉 SCRAPING COMPLETED!")
    print("=" * 70)
    print(f"📊 Results Summary:")
    print(f"   ✅ Successful URLs: {result['stats']['urls_successful']}/{len(urls)}")
    print(f"   ❌ Failed URLs: {result['stats']['urls_failed']}")
    print(f"   📄 Total Records: {result['stats']['total_records']}")
    print()
    print("💾 Generated Files:")
    print(f"   • {output_name}.csv - Main combined data")
    print(f"   • {output_name}_table_data.csv - Table data only")
    print(f"   • {output_name}_version_info.csv - Version information")
    print(f"   • {output_name}_list_item.csv - List items")
    print(f"   • {output_name}_section_content.csv - Section content")
    print(f"   • {output_name}_summary.csv - Scraping summary report")
    print("=" * 70)
    
    return result

def quick_start():
    """Quick start with default configuration."""
    return run_formatted_scraper()

# ==============================================================================
# 7. LEGACY COMPATIBILITY (StaticScraper class)
# ==============================================================================

class StaticScraper:
    """Legacy static scraper for compatibility."""
    def __init__(self, url: str, config: ScraperConfig = None, logger: ScraperLogger = None):
        self.url = url
        self.config = config or ScraperConfig()
        self.logger = logger or ScraperLogger()
    
    def scrape(self) -> str:
        """Simple scrape method."""
        import httpx
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        with httpx.Client(headers=headers, timeout=30) as client:
            response = client.get(self.url)
            response.raise_for_status()
            return response.text

# ==============================================================================
# 8. SCRIPT ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    quick_start()