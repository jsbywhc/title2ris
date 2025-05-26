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
import json
import time
import os
import sys
from urllib.parse import quote

def read_titles(file_path):
    '''
    从标题文件中读取标题
    输入：标题文件路径
    输出：标题列表
    '''
    with open(file_path, 'r', encoding='utf-8') as file:
        titles = [line.strip() for line in file if line.strip()]
    return titles

def get_metadata(title, max_retries=3, timeout=60):
    '''
    从Crossref API获取文章元数据
    输入：标题，最大重试次数，超时时间
    输出：元数据字典
    '''
    encoded_title = quote(title) # URL编码标题，处理空格和特殊字符
    url = f"https://api.crossref.org/works?query={encoded_title}&rows=2" # 请求2个结果，以便在第一个是Supplemental Information时能使用第二个
    headers = {
        'User-Agent': 'Title2RIS/1.0 (mailto:wanghc2023@nanoctr.cn)', # **UA可能需要参考张老师**
    }
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt+1}/{max_retries} for title: {title}")
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()  
            
            data = response.json()
            if data['message']['total-results'] > 0 and len(data['message']['items']) > 0:
                # 检查第一个结果是否为Supplemental Information
                first_result = data['message']['items'][0]
                
                # 检查标题或描述中是否包含Supplemental Information
                is_supplemental = False
                
                if 'title' in first_result:
                    for title_text in first_result['title']:
                        if 'supplemental' in title_text.lower() or 'supporting information' in title_text.lower():
                            is_supplemental = True
                            break
                
                if 'description' in first_result:
                    if isinstance(first_result['description'], list):
                        for desc in first_result['description']:
                            if 'supplemental' in desc.lower() or 'supporting information' in desc.lower():
                                is_supplemental = True
                                break
                    elif isinstance(first_result['description'], str) and ('supplemental' in first_result['description'].lower() or 'supporting information' in first_result['description'].lower()):
                        is_supplemental = True
                
                # 如果第一个结果是补充信息且有第二个结果，则返回第二个结果
                if is_supplemental and len(data['message']['items']) > 1:
                    print(f"First result was Supplemental Information, using second result instead.")
                    return data['message']['items'][1]
                else:
                    return first_result  # 返回第一个结果
            else:
                print(f"No results found for title: {title}")
                return None
        except requests.exceptions.Timeout:
            print(f"Timeout on attempt {attempt+1}/{max_retries}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print(f"Max retries reached for title: {title}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request error on attempt {attempt+1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print(f"Max retries reached for title: {title}")
                return None
        except Exception as e:
            print(f"Error searching for title '{title}': {e}")
            return None

def convert_to_ris(metadata):
    """Convert Crossref metadata to RIS format"""
    if not metadata:
        return ""
    
    ris_lines = []
    
    # 类别：JOUR 表示期刊文章
    ris_lines.append("TY  - JOUR")
    
    # 标题
    if 'title' in metadata and metadata['title']:
        ris_lines.append(f"TI  - {metadata['title'][0]}")
    
    # 作者
    if 'author' in metadata:
        for author in metadata['author']:
            if 'family' in author and 'given' in author:
                ris_lines.append(f"AU  - {author['family']}, {author['given']}")
            elif 'family' in author:
                ris_lines.append(f"AU  - {author['family']}")
    
    # 期刊
    if 'container-title' in metadata and metadata['container-title']:
        ris_lines.append(f"JF  - {metadata['container-title'][0]}") # 期刊全称
    if 'short-container-title' in metadata and metadata['short-container-title']:
        ris_lines.append(f"JN  - {metadata['short-container-title'][0]}") # 期刊简称
    
    # 摘要
    if 'abstract' in metadata and metadata['abstract']:
        ris_lines.append(f"AB  - {metadata['abstract'][0]}")

    # 年份
    published_date = None
    for date_field in ['published-print', 'published-online', 'created']:
        if date_field in metadata and 'date-parts' in metadata[date_field]:
            date_parts = metadata[date_field]['date-parts'][0]
            if date_parts and len(date_parts) > 0:
                published_date = date_parts[0]
                break
    
    if published_date:
        ris_lines.append(f"PY  - {published_date}")
    
    # 卷号，期号，页码
    if 'volume' in metadata:
        ris_lines.append(f"VL  - {metadata['volume']}")
    
    if 'issue' in metadata:
        ris_lines.append(f"IS  - {metadata['issue']}")
    
    if 'page' in metadata:
        ris_lines.append(f"SP  - {metadata['page']}")
    
    # DOI
    if 'DOI' in metadata:
        ris_lines.append(f"DO  - {metadata['DOI']}")
    
    # ISSN
    if 'ISSN' in metadata and metadata['ISSN']:
        ris_lines.append(f"SN  - {metadata['ISSN'][0]}")
    
    # 出版社
    if 'publisher' in metadata:
        ris_lines.append(f"PB  - {metadata['publisher']}")
    
    # 结尾标记符
    ris_lines.append("ER  - ")
    
    return "\n".join(ris_lines)

def write_results(ris_entries, output_file, backup=False):
    try:
        filename = f"{output_file}.backup" if backup else output_file
        with open(filename, 'w', encoding='utf-8') as file:
            file.write("\n\n".join(ris_entries))
        return True
    except Exception as e:
        print(f"Error writing to {filename}: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = input("Enter the path to the text file with titles: ")
    
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        return
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = input("Enter the path for the output RIS file (or press Enter to use 'output.ris'): ")
        if not output_file:
            output_file = "output.ris"
    
    # Read titles
    titles = read_titles(input_file)
    print(f"Read {len(titles)} titles from {input_file}")
    
    # Process each title
    ris_entries = []
    success_count = 0
    
    for i, title in enumerate(titles, 1):
        print(f"\nProcessing title {i}/{len(titles)}:")
        print(f"{title}")
        
        try:
            # Write partial results after each batch
            if success_count > 0 and success_count % 3 == 0:
                print(f"Writing partial results ({success_count} entries so far)...")
                write_results(ris_entries, output_file)
                # Also write a backup just to be safe
                write_results(ris_entries, output_file, backup=True)
            
            # Use a reasonable timeout
            metadata = get_metadata(title, max_retries=3, timeout=20)
            
            if metadata:
                ris = convert_to_ris(metadata)
                if ris:
                    ris_entries.append(ris)
                    success_count += 1
                    print(f"Successfully converted to RIS format")
                else:
                    print(f"Found metadata but failed to convert to RIS")
            else:
                print(f"No metadata found")
            
            # Add a delay between requests
            if i < len(titles):
                wait_time = 3  # 3 seconds between requests
                print(f"Waiting {wait_time} seconds before next request...")
                time.sleep(wait_time)
                
        except KeyboardInterrupt:
            print("\nProcess interrupted by user. Saving partial results...")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
    
    # Write final results
    if ris_entries:
        if write_results(ris_entries, output_file):
            print(f"\nProcessing complete! Saved {success_count} entries to {output_file}")
        else:
            print("\nFailed to save final results to main output file.")
            if write_results(ris_entries, output_file, backup=True):
                print(f"Saved backup to {output_file}.backup")
            else:
                print("Failed to save backup file as well.")
    else:
        print("\nNo entries were successfully processed.")

if __name__ == "__main__":
    main()
