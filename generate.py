import json
import os
import re
import pypandoc
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

if not os.environ.get("GEMINI_API_KEY"):
    raise ValueError("CRITICAL: GEMINI_API_KEY not found. Please create a .env file and add your key.")

def clean_filename(text):
    """Sanitizes strings to be safe for OS file names."""
    if not text:
        return "Unknown"
    # Replace spaces with underscores and strip out non-alphanumeric characters
    clean = re.sub(r'[^a-zA-Z0-9_\-]', '', text.replace(' ', '_'))
    return clean

def generate_collateral(job_req_text):
    # 1. Load Local State
    if not os.path.exists('master_data.json'):
        raise FileNotFoundError("master_data.json is missing. Run the preprocessor script first.")
    
    with open('master_data.json', 'r') as f:
        master_data = json.load(f)

    if not os.path.exists('system_prompt.txt'):
        raise FileNotFoundError("system_prompt.txt is missing.")
        
    with open('system_prompt.txt', 'r') as f:
        system_prompt = f.read()

    # 2. Define the Schema (Now including job_metadata extraction)
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "job_metadata": {
                "type": "OBJECT",
                "properties": {
                    "company_name": {"type": "STRING"},
                    "role_title": {"type": "STRING"}
                }
            },
            "selected_skills": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "tailored_roles": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING"},
                        "company": {"type": "STRING"},
                        "dates": {"type": "STRING"},
                        "bullets": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        }
                    }
                }
            },
            "cover_letter_body": {"type": "STRING"}
        }
    }

    # 3. Call the API
    client = genai.Client()
    user_prompt = f"Job Req:\n{job_req_text}\n\nMaster Data:\n{json.dumps(master_data)}"
    
    print("Initiating Gemini API Call. Extracting meta and filtering history...")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.2 
        )
    )

    # 4. Parse the Response & Generate Filename Prefix
    gemini_output = json.loads(response.text)
    
    # Safely extract company and role, defaulting to "Unknown" if the AI couldn't find them
    meta = gemini_output.get("job_metadata", {})
    company = clean_filename(meta.get("company_name", "UnknownCompany"))
    role = clean_filename(meta.get("role_title", "UnknownRole"))
    
    prefix = f"{company}_{role}"
    print(f"AI Processing Complete. Building collateral for: {prefix}")

    # 5. Inject Data into Jinja2 Templates
    env = Environment(loader=FileSystemLoader('.'))
    resume_template = env.get_template('resume_template.md')
    cover_letter_template = env.get_template('cover_letter_template.md')

    resume_markdown = resume_template.render(
        contact=master_data.get('contact', {}),
        skills_list=gemini_output.get('selected_skills', []),
        experience=gemini_output.get('tailored_roles', [])
    )
    
    cl_markdown = cover_letter_template.render(
        contact=master_data.get('contact', {}),
        cover_letter_body=gemini_output.get('cover_letter_body', '')
    )

    # 6. Compile Final Outputs
    print(f"Compiling {prefix}_Resume.pdf and {prefix}_CoverLetter.pdf...")
    
    # Temporary markdown files
    with open('temp_resume.md', 'w') as f: f.write(resume_markdown)
    with open('temp_cl.md', 'w') as f: f.write(cl_markdown)

    # Convert to PDF
    pypandoc.convert_file('temp_resume.md', 'pdf', outputfile=f'{prefix}_Resume.pdf')
    pypandoc.convert_file('temp_cl.md', 'pdf', outputfile=f'{prefix}_CoverLetter.pdf')

    # Clean up the temporary markdown files so your folder stays clean
    os.remove('temp_resume.md')
    os.remove('temp_cl.md')

    print("Success! Both files have been deployed to your directory.")

if __name__ == "__main__":
    print("--- The JIT Resume Engine ---")
    print("Paste the target Job Requisition below. Press Enter, then CTRL+D (or CMD+D) to submit:\n")
    
    import sys
    req_input = sys.stdin.read()
    
    if req_input.strip():
        generate_collateral(req_input)
    else:
        print("No input detected. Exiting.")