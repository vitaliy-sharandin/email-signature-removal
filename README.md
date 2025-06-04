# Data
- To test the solution the 2GB dump of personal emails data from Gmail in `.eml` format was extracted.
- `88 emails` were selected for final tests given their variety of language and format to save resources and time.

# Approaches tested
- [Mailgun Talon](https://github.com/mailgun/talon)
    - Seemed like a great library to start with, yet unmaintained and incompatible with python>3.11 because of dependency conflicts
- Regex
    - Good for predictable signatures
    - Very limited solution which is bad at unpredictable and content flexible signatures containing images or web links.
    - Limited to manual language selection phrases detection if you base your gerex on common words.
- Local reasoning model
    - `QwQ:32b` qwen latest reasoning model on 4090 GPU was tested.
    - Whole processing of 88 emails took `~40min` so around `30sec/email`
    - Very impressive solution which mostly did the job with `80%` success rate.
    - The only downside is model had trouble with returning exact mail content when content had many long web links, instead it was summarizing content.
- OpenAI gpt-4o API
    - Superior solution which perfectly extracts data other than signatures and returns original content in with `99%` success rate.
    - Multiple signature formats, data appendices and languages supported out of the box.
    - Cost `0.008$` per email, overall `0.74$` for 88 emails.

# Chosen solution
OpenAI `gpt-4o` API is a clear winner, as it does the job with single request and `99%` success rate.

# Running solution
1. Create and fill the .env file with environment variables.
```
EML_EMAILS_FOLDER=
OPENAI_API_KEY=
```
2. Use uv package management tool 
    - Install uv package management tool and `uv sync`
    OR
    - `pip install -r requirements.txt`
3. Run python script `email_content_parser.py`.

# Output
The results will appear in `output/email_comparison_datemetime.csv` file, where you can verify emails manually side by side or continue processing them automatically later.
