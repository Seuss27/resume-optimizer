# Resume Optimizer 📄🚀

**A "Resume-as-Code" pipeline, because manually tweaking MS Word layouts is nonsense. This Python script feeds a job req and your compiled CSV history into the Gemini API, extracts matching skills, and uses Jinja2 and Pandoc to compile ATS-friendly Word documents (.docx). It is basically CI/CD for your career collateral.**

## Architecture Overview

Instead of maintaining dozens of fragmented resume files, this project separates your **State** (who you are and what you've done) from your **Presentation** (the final .docx file).

When you find a job you want to apply for, the engine:
1. **Compiles State:** The `build_state.py` preprocessor merges your raw `experience.csv` and `profile.csv` into a single structured JSON state file.
2. **Filters via AI:** The `generate.py` engine passes the Job Requisition and your state file to the **Gemini API**. The AI acts as a smart filter, returning only the most relevant skills and bullet points, while extracting the Company Name and Role Title.
3. **Injects & Renders:** The filtered data is injected into dedicated **Jinja2 Markdown templates** for both a resume and a cover letter.
4. **Deploys:** **Pandoc** compiles the customized Markdown into two perfectly formatted Word documents, dynamically named based on the requisition (e.g., `AcmeCorp_BackendEngineer_Resume.docx`).

## Prerequisites

* **Python 3.8+**
* **Pandoc** (The script will attempt to automatically download the Pandoc engine if it is not found on your system)
* **Gemini API Key** (Get one at [Google AI Studio](https://aistudio.google.com/))

## Installation

1. **Clone the repository:**
```bash
   git clone [https://github.com/YOUR_USERNAME/resume-optimizer.git](https://github.com/YOUR_USERNAME/resume-optimizer.git)
   cd resume-optimizer
   ```

2. **Set up a virtual environment:**
```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. **Install dependencies:**
```bash
   pip install -r requirements.txt
   ```

## Configuration & Security

⚠️ **IMPORTANT:** Your career history and API keys are sensitive. This repository is pre-configured with a `.gitignore` to prevent tracking your personal CSVs, JSON state, and credentials.

1. **Configure your API Key:**
   Create a file named `.env` in the root directory and add your key:
```text
   GEMINI_API_KEY="your_actual_api_key_here"
   ```

2. **Hydrate your Data:**
   * This project includes dummy templates to demonstrate the required data schema. 
   * Copy `example_profile.csv` and rename it to `profile.csv`, then update it with your actual contact info.
   * Copy `example_experience.csv` and rename it to `experience.csv`, then populate it with your tabular work history.
   * *(Note: Your actual `profile.csv` and `experience.csv` files are ignored by git to protect your privacy).*

## Usage

**Step 1: Build your local state**
Whenever you update your master spreadsheets, run the preprocessor to generate your `master_data.json`:
```bash
python build_state.py
```

**Step 2: Generate Collateral**
Run the core engine and paste the text of the job description when prompted.
When finished pasting, press `Enter`, then `CTRL+D` (Mac/Linux) or `CTRL+Z` then `Enter` (Windows) to submit:
```bash
python generate.py
```

Check your project directory for your freshly deployed `[Company]_[Role]_Resume.docx` and `[Company]_[Role]_CoverLetter.docx`.

## Project Structure

* `generate.py` - The core application engine (API call, data injection, DOCX compilation).
* `build_state.py` - The data preprocessor (CSV to JSON).
* `resume_template.md` - Jinja2 layout for the resume.
* `cover_letter_template.md` - Jinja2 layout for the cover letter.
* `system_prompt.txt` - The strict instructional persona fed to the Gemini API.
* `example_profile.csv` & `example_experience.csv` - Dummy data templates to guide your CSV creation.
* `requirements.txt` - Python dependencies.