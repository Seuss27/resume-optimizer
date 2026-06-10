# Resume Optimizer 📄🚀

**A "Resume-as-Code" pipeline, because manually tweaking MS Word layouts is nonsense. This Python script feeds a job req and your compiled CSV history into the Gemini API, extracts matching skills, and uses Jinja2 and Pandoc to compile ATS-friendly Word documents (.docx). It is basically CI/CD for your career collateral.**

## Architecture Overview

Instead of maintaining dozens of fragmented resume files, this project separates your **State** (who you are and what you've done) from your **Presentation** (the final .docx file).

When you find a job you want to apply for, the engine:
1. **Compiles State:** The `build_state.py` preprocessor merges your raw `experience.csv` and `profile.csv` into a single structured JSON state file.
2. **Filters via AI:** The `generate.py` engine passes the Job Requisition and your state file to the **Gemini API**. The AI acts as a smart filter, returning only the most relevant skills and bullet points, while extracting the Company Name and Role Title.
3. **Optional ATS audit:** If run with `--validate`, the generated resume text is re-checked with a second Gemini review using `ats_prompt.txt`, producing a compatibility score, missing keyword list, and actionable feedback.
4. **Optional Job Evaluation:** If run with `--score-job`, the original job req is evaluated against your personal preferences (`desirability_prompt.txt`), analyzing salary match, remote capabilities, and core pros/cons.
5. **Injects & Renders:** The filtered data is injected into dedicated **Jinja2 Markdown templates** for both a resume and a cover letter. (The intermediate markdown files are cleanly removed unless `--preserve-markdown` is used).
6. **Deploys:** **Pandoc** compiles the customized Markdown into two perfectly formatted Word documents, dynamically named based on the requisition (e.g., `AcmeCorp_BackendEngineer_Resume.docx`).

## Prerequisites

* **Python 3.10+**
* **Pandoc** (The script will attempt to automatically download the Pandoc engine if it is not found on your system)
* **Gemini API Key** (Get one at [Google AI Studio](https://aistudio.google.com/))

## Installation & Setup

Choose **one** of the following environment options to install and run the workspace.

### Option A: Clean Workspace via Hatch (Recommended)
This method utilizes [Hatch](https://hatch.pypa.io/) to natively manage virtual runtimes, dependencies, and execution mappings in an isolated system cache without cluttering your local directory.

1. **Install Hatch globally** (via pipx or your global python layer):
   ```bash
   pipx install hatch
   ```
2. **Clone the repository and enter the workspace:**
   ```bash
   git clone [https://github.com/Seuss27/resume-optimizer.git](https://github.com/Seuss27/resume-optimizer.git)
   cd resume-optimizer
   ```
3. Everything is ready! Hatch will build and hydrate your environment on your first execution script call.

### Option B: Traditional Virtual Environment via Pip
If you prefer a standard local virtual environment workflow using standard python packaging paths:

1. **Clone the repository and enter the workspace:**
   ```bash
   git clone [https://github.com/Seuss27/resume-optimizer.git](https://github.com/Seuss27/resume-optimizer.git)
   cd resume-optimizer
   ```
2. **Set up and activate your virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```
3. **Install the package and development dependencies in editable mode:**
   ```bash
   pip install --upgrade pip
   pip install -e .[dev]
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

Depending on your installation path chosen above, run the preprocessor followed by the core AI engine:

### If Using Hatch (Option A)
```bash
# Step 1: Preprocess your CSVs into unified JSON state
hatch run build-state

# Step 2: Paste the target job requisition text to compile outputs
hatch run generate

# Optional: compile outputs, run ATS validation, evaluate job desirability, and preserve markdown files
hatch run generate -- --validate --score-job --preserve-markdown
```

### If Using Standard Pip Entry Points (Option B)
```bash
# Step 1: Preprocess your CSVs into unified JSON state
build-resume-state

# Step 2: Paste the target job requisition text to compile outputs
generate-resume

# Optional: compile outputs and run ATS validation
generate-resume --validate
```

*When running the generation engine, paste the text of the job description when prompted. When finished pasting, press `Enter`, then `CTRL+D` (Mac/Linux) or `CTRL+Z` then `Enter` (Windows) to submit.*

Check your root project directory for your freshly deployed `[Company]_[Role]_Resume.docx` and `[Company]_[Role]_CoverLetter.docx`.

## Development Commands

For developers validating changes or contributing to the repository, workspace checks are exposed natively via Hatch:

```bash
hatch run test    # Run unit testing suite via pytest
hatch run lint    # Validate style and security rules via ruff check
hatch run format  # Apply automated codebase formatting via ruff format
```

## Project Structure

```text
resume-optimizer/
├── .github/
│   ├── dependabot.yml       # Dependency tracking configuration
│   └── workflows/ci.yml     # Automated multi-environment GitHub Actions pipeline
├── src/
│   └── resume_optimizer/
│       ├── __init__.py      # Package indicator
│       ├── build_state.py   # Data preprocessor (CSV to JSON)
│       ├── generate.py      # Core AI engine (Gemini API, templates, compilation)
│       └── logging_setup.py # Unified structured logging configuration
├── tests/                   # Complete unit test suite
├── resume_template.md       # Jinja2 layout for the resume
├── cover_letter_template.md # Jinja2 layout for the cover letter
├── resume_reference.docx    # MS Word styles reference document used by Pandoc
├── system_prompt.txt        # Recruiter instructional alignment token fed to Gemini
├── ats_prompt.txt           # ATS validation system prompt used by the optional review pass
├── desirability_prompt.txt  # Job desirability evaluation prompt for --score-job
├── tune_template.py         # Utility script for tuning MS Word outputs locally
├── dummy_gemini_output.json # Mock AI data payload used by tune_template.py
├── pyproject.toml           # Declarative tool settings, dependencies, and metadata
└── .pre-commit-config.yaml  # Local Git compliance commit hook mapping
```