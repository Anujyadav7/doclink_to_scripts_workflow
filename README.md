# Google Docs Bulk Extractor

This tool automates the process of extracting text scripts from multiple Google Docs links using a persistent browser session. It behaves like a real user by opening the document, copying the text, and saving it to a local text file.

## Prerequisites
1. Python 3.8+ installed
2. `pip` installed

## Setup Instructions

1. Clone or download this repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browsers (required for the automation to work):
   ```bash
   playwright install
   ```

## Usage

1. Open the file named `input_links.txt`.
2. Paste your Google Doc links and their corresponding titles. You can copy-paste directly from Excel or Google Sheets. The format should be:
   ```text
   https://docs.google.com/document/d/...    "Course Title 1"
   https://docs.google.com/document/d/...    "Course Title 2"
   ```
3. Run the script:
   ```bash
   python extract_scripts.py
   ```

### Notes
- The script uses a persistent Playwright context (`playwright_data/` folder). This means if any Google Doc requires login, you will only need to log in the first time the browser opens. Future runs will remember your session!
- The extracted scripts will be appended to `extracted_scripts.txt`.
- No API keys or proxy settings are required.
