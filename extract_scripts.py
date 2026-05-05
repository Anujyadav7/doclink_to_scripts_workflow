import os
import re
import time
import asyncio
import pyperclip
from playwright.async_api import async_playwright

def parse_input_file(filepath: str):
    """Safely extracts URL and title even if pasted from Excel/Sheets with newlines/tabs."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    parts = re.split(r'(https://docs\.google\.com/[^\s]+)', content)
    tasks = []
    
    for i in range(1, len(parts), 2):
        url = parts[i]
        
        # Handle the weird paste format where URL and title are stuck together
        if "usp=sharing" in url and not url.endswith("usp=sharing"):
            actual_url = url[:url.find("usp=sharing")+11]
            title_text = url[url.find("usp=sharing")+11:] + " " + (parts[i+1] if i+1 < len(parts) else "")
        else:
            actual_url = url
            title_text = parts[i+1] if i+1 < len(parts) else ""
            
        title = title_text.replace('\n', ' ').replace('\t', ' ').strip()
        title = re.sub(r' +', ' ', title).replace('"', '').replace("'", "")
        
        if not title or title.startswith("#"):
            title = f"Document {len(tasks)+1}"
            
        tasks.append((actual_url, title))
        
    return tasks

async def extract_google_doc_text(page, url: str, retries: int = 3) -> str:
    """Extracts text from a Google Doc using Playwright and Clipboard."""
    print(f"\n--- Loading Document: {url} ---")
    
    for attempt in range(retries):
        try:
            print(f"Attempt {attempt + 1}: Navigating...")
            pyperclip.copy("") # Clear clipboard
            
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            current_url = page.url
            if "ServiceLogin" in current_url or "accounts.google.com" in current_url:
                print("\n[!] Login Required! Please log in on the opened browser window.")
                print("[!] Waiting up to 120 seconds for you to complete login...")
                try:
                    await page.wait_for_url("**/docs.google.com/**", timeout=120000)
                    print("Login successful! Proceeding to load document...")
                    await page.wait_for_timeout(3000)
                except Exception:
                    raise Exception("Login timed out or failed. Please try again.")
            
            try:
                await page.wait_for_selector(".kix-appview-editor", timeout=15000)
                await page.click(".kix-appview-editor")
            except Exception:
                print("Standard editor not found, attempting generic copy on body...")
                await page.wait_for_selector("body", timeout=10000)
                await page.click("body")
                
            await page.wait_for_timeout(1000)
            
            print("Copying text...")
            await page.keyboard.press("Control+A")
            await page.wait_for_timeout(500)
            await page.keyboard.press("Control+C")
            await page.wait_for_timeout(1000)
            
            clipboard_text = pyperclip.paste()
            
            if clipboard_text and len(clipboard_text.strip()) > 10:
                print(f"Successfully extracted {len(clipboard_text)} characters.")
                return clipboard_text
            else:
                print("Clipboard was empty or too short. Retrying...")
                
        except Exception as e:
            print(f"Error during extraction attempt {attempt + 1}: {e}")
        
        await page.wait_for_timeout(2000)
        
    raise Exception(f"Failed to extract content from Google Doc: {url}")

def clean_extracted_text(text: str) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return "\n".join(cleaned_lines)

async def main():
    print("=== Google Docs Bulk Extractor ===")
    
    input_file = "input_links.txt"
    output_file = "extracted_scripts.txt"
    
    if not os.path.exists(input_file):
        with open(input_file, "w", encoding="utf-8") as f:
            f.write("# Paste your Google Doc links and titles below (just copy-paste from Excel/Sheets)\n")
        print(f"\n[!] Created '{input_file}'. Please open it, paste your links and titles, save it, and run the script again.")
        return
        
    tasks = parse_input_file(input_file)
    valid_tasks = [t for t in tasks if t[0] and "http" in t[0]]
    if not valid_tasks:
        print(f"\n[!] No valid Google Doc links found in '{input_file}'.")
        return
        
    print(f"\nFound {len(valid_tasks)} documents to extract!")
    
    with open(output_file, "a", encoding="utf-8") as out_f:
        out_f.write("\n\n" + "="*80 + f"\nBATCH EXTRACTION START: {time.ctime()}\n" + "="*80 + "\n\n")
    
    async with async_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), "playwright_data")
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            permissions=['clipboard-read', 'clipboard-write']
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        for idx, (doc_link, title) in enumerate(valid_tasks):
            print(f"\n[{idx+1}/{len(valid_tasks)}] Processing: {title}")
            
            try:
                raw_text = await extract_google_doc_text(page, doc_link)
                cleaned_text = clean_extracted_text(raw_text)
                
                # Extract title from the first line of the document if no title was provided
                actual_title = title
                if actual_title.startswith("Document "):
                    lines = cleaned_text.splitlines()
                    if lines:
                        actual_title = lines[0].strip()
                
                # Format output
                final_output = f"TITLE: {actual_title}\n"
                final_output += f"LINK: {doc_link}\n"
                final_output += "-"*80 + "\n"
                final_output += cleaned_text + "\n"
                final_output += "="*80 + "\n\n"
                
                with open(output_file, "a", encoding="utf-8") as out_f:
                    out_f.write(final_output)
                    
                print(f"[{idx+1}/{len(valid_tasks)}] Success! Script saved to {output_file}.")
                
            except Exception as e:
                print(f"[{idx+1}/{len(valid_tasks)}] Failed: {e}")
                
        await context.close()
        
    print(f"\n=== All Done! Check '{output_file}' for your extracted scripts. ===")

if __name__ == "__main__":
    asyncio.run(main())
