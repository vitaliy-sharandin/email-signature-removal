import csv
import email
import glob
import os
import re
import time
from datetime import datetime

import ollama
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.schema import HumanMessage
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv()

EML_FILES_FOLDER = os.getenv("EML_EMAILS_FOLDER", "emails/")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key")

PROMPT = """
        You are an expert email signature cleaner.

        TASK:
        - Remove all email signatures and content related to them and leave only original message content.
        - Preserve all email content text, images, linkes in original form.
        
        RULES:
        - Email signatures can appear multiple times and not only at the end.
        - A signature is any block that includes combinations of:
            - Person's name, job title, contact info (phone, email, address)
            - Company name, legal disclaimer, or social media links
            - Closings like "Best regards", "Sincerely", "Cheers", etc.
            - Logos or image tags
        - Remove all such blocks wherever they appear in the email.
        - Do NOT remove any actual message content, even if it's after a signature.
        - Do NOT summarize the email content.

        EXAMPLES:
            INPUT EMAIL:
                Hello John,
                I hope this message finds you well. Please find attached the report we discussed.
                (http://example.com/report.pdf)
                Best regards,
                Jane Doe
            CORRECT OUTPUT:
                Hello John,
                I hope this message finds you well. Please find attached the report we discussed.
                (http://example.com/report.pdf)
            WRONG OUTPUT 1 (did not remove signature):
                Hello John,
                I hope this message finds you well. Please find attached the report we discussed.
                Best regards,
                Jane Doe
            WRONG OUTPUT 2 (created summary):
                Jane Doe sent an email to John with a report attached. The email starts with a greeting and ends with a closing.

        INPUT EMAIL:
        {email_content}
        """


def initialize_csv(output_filename=None):
    """
    Initialize CSV file with headers
    """
    if output_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"output/email_comparison_{timestamp}.csv"

    os.makedirs(os.path.dirname(output_filename), exist_ok=True)

    with open(output_filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
        writer.writerow(
            ["Email_ID", "Original_Email", "Cleaned_Email", "Processing_Status"]
        )

    return output_filename


def append_to_csv(email_id, original_content, cleaned_content, status, csv_filename):
    """
    Append email data to existing CSV file
    """
    try:
        with open(csv_filename, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
            writer.writerow([email_id, original_content, cleaned_content, status])

        print(f"Email {email_id} added to CSV")
        return True

    except Exception as e:
        print(f"Error appending to CSV: {e}")
        return False


def process_multiple_emails(email_folder_path, csv_output_filename=None):
    """
    Process multiple .eml files and save to CSV
    """
    csv_filename = initialize_csv(csv_output_filename)

    eml_files = glob.glob(os.path.join(email_folder_path, "*.eml"))

    if not eml_files:
        print(f"No .eml files found in {email_folder_path}")
        return

    print(f"Found {len(eml_files)} email files to process")

    for idx, eml_file in enumerate(eml_files, 1):
        try:
            print(
                f"\nProcessing email {idx}/{len(eml_files)}: {os.path.basename(eml_file)}"
            )

            with open(eml_file, "r", encoding="utf-8") as file:
                email_message = email.message_from_file(file)

            email_content = ""
            cleaned_content = ""

            if email_message.is_multipart():
                for part in email_message.walk():
                    email_content += parse_mail_content(part)
            else:
                email_content = parse_mail_content(email_message)

            if email_content.strip():
                try:
                    cleaned_content = openai_signature_removal(email_content)

                    status = "Success"

                except Exception as e:
                    status = f"LLM Error: {str(e)}"
                    print(f"LLM processing failed for {eml_file}: {e}")

                email_id = os.path.basename(eml_file)
                append_to_csv(
                    email_id, email_content, cleaned_content, status, csv_filename
                )

            else:
                print(f"No text content found in {eml_file}")
                append_to_csv(
                    os.path.basename(eml_file),
                    "No content",
                    "No content",
                    "No text content",
                    csv_filename,
                )

        except Exception as e:
            print(f"Error processing {eml_file}: {e}")
            append_to_csv(
                os.path.basename(eml_file),
                "Error reading file",
                "Error reading file",
                f"File Error: {str(e)}",
                csv_filename,
            )
    return csv_filename


def parse_mail_content(message):
    content = ""
    ctype = message.get_content_type()
    if ctype == "text/plain":
        plain = message.get_payload(decode=True).decode(
            message.get_content_charset() or "utf-8", "replace"
        )
        content = plain
    elif ctype == "text/html":
        html = message.get_payload(decode=True).decode(
            message.get_content_charset() or "utf-8", "replace"
        )
        soup = BeautifulSoup(html, "html.parser")
        content = soup.get_text(separator=" ", strip=True)

        content = re.sub(r"\s+", " ", content)
        content = re.sub(r"\n\s*\n", "\n", content)
        content = content.strip()
    return content


def openai_signature_removal(email_content):
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        api_key=OPENAI_API_KEY,
    )
    llm_response = llm.invoke(
        [
            HumanMessage(content=PROMPT.format(email_content=email_content)),
        ]
    )
    cleaned_content = llm_response.content
    return cleaned_content


def local_llm_signature_removal(email_content):
    response = ollama.chat(
        model="qwq:32b",
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(email_content=email_content),
            },
        ],
        options={
            "temperature": 0.1,
        },
    )["message"]["content"]

    pattern = r"<think>.*?</think>"
    cleaned_content = re.sub(pattern, "", response, flags=re.DOTALL).strip()
    return cleaned_content


if __name__ == "__main__":
    start_time = time.time()
    start_datetime = datetime.now()

    csv_filename = process_multiple_emails(EML_FILES_FOLDER)

    end_time = time.time()
    end_datetime = datetime.now()
    duration = end_time - start_time

    print(f"\n{'=' * 50}")
    print(
        f"Signature removal completed at: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(
        f"Total processing time: {duration:.2f} seconds ({duration / 60:.2f} minutes)"
    )
    print(f"Results saved to: {csv_filename}")
    print(f"{'=' * 50}")
