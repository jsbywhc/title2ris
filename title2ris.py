# title2ris.py
# Wang HC
# 2025-05-24
"""
将标题转换为RIS格式的脚本

使用方法：
    python title2ris.py <标题文件路径> <输出文件路径>
        或者
    python title2ris.py 后手动输入标题文件路径和输出文件路径
"""
import requests
import time
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from typing import List, Dict, Optional, Union
import argparse
from pathlib import Path

from config import (
    CROSSREF_API_URL, USER_AGENT, API_TIMEOUT, MAX_RETRIES,
    WAIT_TIME_BETWEEN_REQUESTS, BATCH_SIZE, SKIP_TITLES,
    DEFAULT_OUTPUT_FILE, ENCODING, MAX_WORKERS
)
from logger import logger


class RateLimiter:
    def __init__(self, rate: float, burst: int = 10):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                time.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1

class Title2RISError(Exception):
    """Base exception for Title2RIS application"""
    pass

class APIError(Title2RISError):
    """API related errors"""
    pass

class FileOperationError(Title2RISError):
    """File operation related errors"""
    pass

def validate_file_path(file_path: Union[str, Path], should_exist: bool = True) -> Path:
    """
    Validate file path and return Path object
    
    Args:
        file_path: File path to validate
        should_exist: Whether the file should exist
        
    Returns:
        Path object
        
    Raises:
        FileOperationError: If validation fails
    """
    try:
        path = Path(file_path)
        if should_exist and not path.exists():
            raise FileOperationError(f"File not found: {file_path}")
        if should_exist and not path.is_file():
            raise FileOperationError(f"Path is not a file: {file_path}")
        return path
    except Exception as e:
        raise FileOperationError(f"Invalid file path '{file_path}': {str(e)}")

def read_titles(file_path: Union[str, Path]) -> List[str]:
    '''
    从标题文件中读取标题
    输入：标题文件路径
    输出：标题列表
    '''
    path = validate_file_path(file_path)
    try:
        with path.open('r', encoding=ENCODING) as file:
            titles = [line.strip() for line in file if line.strip()]
        logger.info(f"Successfully read {len(titles)} titles from {file_path}")
        return titles
    except Exception as e:
        raise FileOperationError(f"Error reading titles from {file_path}: {str(e)}")

def get_metadata(title: str, max_retries: int = MAX_RETRIES, timeout: int = API_TIMEOUT) -> Optional[Dict]:
    '''
    从Crossref API获取文章元数据
    输入：标题，最大重试次数，超时时间
    输出：元数据字典
    '''
    if not title:
        logger.warning("Empty title provided")
        return None
        
    encoded_title = quote(title)
    url = f"{CROSSREF_API_URL}?query={encoded_title}&rows=5"
    headers = {'User-Agent': USER_AGENT}
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt+1}/{max_retries} for title: {title}")
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('message', {}).get('total-results', 0):
                logger.warning(f"No results found for title: {title}")
                return None
                
            items = data['message'].get('items', [])
            if not items:
                logger.warning(f"No items in response for title: {title}")
                return None
                
            # Find first non-special result
            for i, result in enumerate(items):
                if not is_special_title(result):
                    if i > 0:
                        logger.info(f"Skipped {i} special case result(s), using result {i+1}")
                    return result
            
            logger.warning("All results appear to be special cases, using first result as fallback")
            return items[0]
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt+1}/{max_retries}")
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 60)  # Cap wait time at 60 seconds
                logger.info(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                logger.error(f"Max retries reached for title: {title}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on attempt {attempt+1}/{max_retries}: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 60)
                logger.info(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                raise APIError(f"Failed to fetch metadata after {max_retries} attempts: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error searching for title '{title}': {str(e)}")
            raise APIError(f"Unexpected error: {str(e)}")

def is_special_title(result: Dict) -> bool:
    """
    Check if the result contains a special title that should be skipped
    """
    # Check title
    if 'title' in result:
        for title_text in result['title']:
            title_lower = title_text.lower()
            for skip in SKIP_TITLES:
                skip_lower = skip.lower()
                # Complete match
                if title_lower == skip_lower:
                    return True
                # Starts with special title followed by colon or space
                if title_lower.startswith(f"{skip_lower}:") or title_lower.startswith(f"{skip_lower} "):
                    # For short words (like SI), ensure it's a standalone word
                    if len(skip_lower) <= 3:
                        if title_lower.startswith(skip_lower):
                            return True
                    else:
                        return True
    
    # Check description
    if 'description' in result:
        descriptions = result['description']
        if isinstance(descriptions, str):
            descriptions = [descriptions]
        elif not isinstance(descriptions, list):
            return False
            
        for desc in descriptions:
            if any(skip.lower() in desc.lower() for skip in SKIP_TITLES):
                return True
    
    return False

def convert_to_ris(metadata: Optional[Dict]) -> Optional[str]:
    """Convert Crossref metadata to RIS format"""
    if not metadata:
        return None
    
    try:
        ris_lines = ["TY  - JOUR"]  # Start with article type
        
        # Title
        if metadata.get('title'):
            title_index = 0
            for i, title_text in enumerate(metadata['title']):
                if not any(skip.lower() in title_text.lower() for skip in SKIP_TITLES):
                    title_index = i
                    break
            ris_lines.append(f"TI  - {metadata['title'][title_index].strip()}")
        
        # Authors
        for author in metadata.get('author', []):
            author_name = []
            if 'family' in author:
                author_name.append(author['family'])
            if 'given' in author:
                author_name.append(author['given'])
            if author_name:
                ris_lines.append(f"AU  - {', '.join(author_name)}")
        
        # Journal information
        if metadata.get('container-title'):
            ris_lines.append(f"JF  - {metadata['container-title'][0]}")
        if metadata.get('short-container-title'):
            ris_lines.append(f"JN  - {metadata['short-container-title'][0]}")
        
        # Abstract
        if metadata.get('abstract'):
            import re
            abstract_text = metadata['abstract']
            if isinstance(abstract_text, list):
                abstract_text = abstract_text[0]
            # Clean up abstract text
            abstract_text = abstract_text.replace('\u003C', '<').replace('\u003E', '>')
            abstract_text = re.sub('<[^<]+?>', '', abstract_text)
            abstract_text = abstract_text.replace('\n', ' ').strip()
            ris_lines.append(f"AB  - {abstract_text}")
        
        # Publication date
        for date_field in ['published-print', 'published-online', 'created']:
            if date_field in metadata:
                date_parts = metadata[date_field].get('date-parts', [[]])[0]
                if date_parts and len(date_parts) > 0:
                    ris_lines.append(f"PY  - {date_parts[0]}")
                    break
        
        # Volume, Issue, Page
        if metadata.get('volume'):
            ris_lines.append(f"VL  - {metadata['volume']}")
        if metadata.get('issue'):
            ris_lines.append(f"IS  - {metadata['issue']}")
        if metadata.get('page'):
            ris_lines.append(f"SP  - {metadata['page']}")
        
        # DOI
        if metadata.get('DOI'):
            ris_lines.append(f"DO  - {metadata['DOI']}")
        
        # ISSN
        if metadata.get('ISSN'):
            ris_lines.append(f"SN  - {metadata['ISSN'][0]}")
        
        # Publisher
        if metadata.get('publisher'):
            ris_lines.append(f"PB  - {metadata['publisher']}")
        
        # End record
        ris_lines.append("ER  - ")
        
        return "\n".join(ris_lines)
    except Exception as e:
        logger.error(f"Error converting metadata to RIS format: {str(e)}")
        return None

def write_results(ris_entries: List[str], output_file: Union[str, Path], backup: bool = False) -> bool:
    """Write RIS entries to file"""
    try:
        path = Path(output_file)
        if backup:
            path = path.with_suffix(path.suffix + '.backup')
            
        with path.open('w', encoding=ENCODING) as file:
            file.write("\n\n".join(ris_entries))
            
        logger.info(f"Successfully wrote {len(ris_entries)} entries to {path}")
        return True
    except Exception as e:
        logger.error(f"Error writing to {path}: {str(e)}")
        return False

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Convert article titles to RIS format")
    parser.add_argument('input_file', nargs='?', help="Path to input file containing titles")
    parser.add_argument('output_file', nargs='?', help="Path to output RIS file")
    return parser.parse_args()

def process_single_title(title: str, index: int, total: int, rate_limiter: RateLimiter) -> tuple:
    """Process a single title and return (index, title, ris_entry or None)"""
    rate_limiter.acquire()
    logger.info(f"Processing title {index}/{total}: {title[:50]}...")
    
    try:
        metadata = get_metadata(title)
        if metadata:
            ris = convert_to_ris(metadata)
            if ris:
                logger.info(f"[{index}/{total}] Success: {title[:40]}...")
                return (index, title, ris)
            else:
                logger.warning(f"[{index}/{total}] Metadata found but RIS conversion failed")
        else:
            logger.warning(f"[{index}/{total}] No metadata found")
        return (index, title, None)
    except Exception as e:
        logger.error(f"[{index}/{total}] Error: {str(e)}")
        return (index, title, None)


def process_titles_parallel(titles: List[str], output_file: str) -> List[str]:
    """Process titles in parallel using ThreadPoolExecutor"""
    rate_limiter = RateLimiter(rate=1.0/WAIT_TIME_BETWEEN_REQUESTS, burst=MAX_WORKERS)
    results = [None] * len(titles)
    ris_entries = []
    success_count = 0
    
    logger.info(f"Starting parallel processing with {MAX_WORKERS} workers...")
    
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_index = {
                executor.submit(process_single_title, title, i+1, len(titles), rate_limiter): i
                for i, title in enumerate(titles)
            }
            
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    index, title, ris = future.result()
                    results[idx] = ris
                    
                    if ris:
                        success_count += 1
                        
                    if success_count > 0 and success_count % BATCH_SIZE == 0:
                        current_entries = [r for r in results if r is not None]
                        logger.info(f"Saving checkpoint ({len(current_entries)} entries)...")
                        write_results(current_entries, output_file, backup=True)
                        
                except Exception as e:
                    logger.error(f"Future error for index {idx}: {str(e)}")
                    
    except KeyboardInterrupt:
        logger.warning("Interrupted! Saving partial results...")
        
    ris_entries = [r for r in results if r is not None]
    logger.info(f"Completed: {len(ris_entries)}/{len(titles)} successful")
    return ris_entries


def main():
    try:
        args = parse_arguments()
        
        if args.input_file:
            input_file = args.input_file
        else:
            input_file = input("Enter the path to the text file with titles: ").strip()
        
        input_path = validate_file_path(input_file)
        
        if args.output_file:
            output_file = args.output_file
        else:
            output_file = input(f"Enter the path for the output RIS file (or press Enter to use '{DEFAULT_OUTPUT_FILE}'): ").strip()
            if not output_file:
                output_file = DEFAULT_OUTPUT_FILE
        
        titles = read_titles(input_path)
        logger.info(f"Read {len(titles)} titles from {input_path}")
        
        ris_entries = process_titles_parallel(titles, output_file)
        
        if ris_entries:
            if write_results(ris_entries, output_file):
                logger.info(f"Processing complete! Saved {len(ris_entries)} entries to {output_file}")
            else:
                logger.error("Failed to save final results.")
                write_results(ris_entries, output_file, backup=True)
        else:
            logger.warning("No entries were successfully processed.")
            
    except KeyboardInterrupt:
        logger.error("Program interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
