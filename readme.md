# Resume Optimizer 📄🚀

**A "Resume-as-Code" pipeline, because manually tweaking MS Word layouts is nonsense. This Python script feeds a job req and your compiled CSV history into the Gemini API, extracts matching skills, and uses Jinja2 and Pandoc to compile ATS-friendly Word documents (.docx). It is basically CI/CD for your career collateral.**

## Architecture Overview

Instead of maintaining dozens of fragmented resume files, this project separates your **State** (who you are and what you've done) from your **Presentation** (the final .docx file).

When you find a job you want to apply for, the engine:

1. **Compiles State:** The `build_state.py` preprocessor merges your raw `experience.csv` and `profile.csv` into a single structured JSON state file.
2. **Filters via AI:** The `generate.py` engine passes the Job Requisition and your career data, without the contact block, to the **Gemini API**. The AI acts as a smart filter, returning only the most relevant skills and bullet points, while extracting the Company Name and Role Title.
3. **Optional ATS audit:** If run with `--validate`, the generated resume text is re-checked with a second Gemini review using `ats_prompt.txt`, producing a compatibility score, missing keyword list, and actionable feedback.
4. **Optional Job Evaluation:** If run with `--score-job`, the original job req is evaluated against your personal preferences (`desirability_prompt.txt`), analyzing salary match, remote capabilities, and core pros/cons.
5. **Injects & Renders:** The filtered data is injected into dedicated **Jinja2 Markdown templates** for both a resume and a cover letter. (The intermediate markdown files are cleanly removed unless `--preserve-markdown` is used).
6. **Deploys:** **Pandoc** compiles the customized Markdown into two perfectly formatted Word documents, dynamically named based on the requisition (e.g., `AcmeCorp_BackendEngineer_Resume.docx`).
7. **Master Mode:** If run with the `--master` flag, the engine bypasses the job requisition requirement, skips the cover letter, and generates a comprehensive, fully-compiled "Master Resume" containing all historical data from your state file.

## Prerequisites

* **Python 3.14+**
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

1. **Store your API key in the OS keyring:**

   ```bash
   hatch run python -m keyring set resume-optimizer gemini-api-key
   ```

   Under Option B, with the venv active, drop the `hatch run` prefix.
   Enter the key at the prompt, never on the command line. The tool reads it from the keyring only.
   A `.env` file from an earlier version is no longer read: move its key into the keyring, then
   delete the file, and remove any `GEMINI_API_KEY` export from your shell profile too.

   `LLM_PROVIDER` (default `gemini`) is an ordinary environment variable that you set in the
   shell. It is not read from a file. This repo must never hold credentials.

2. **Hydrate your Data:**
   * This project includes dummy templates to demonstrate the required data schema.
   * Put your data in `RO_LEDGER_DIR`. Plan §3.1 gives its default, and the repo checkout itself is refused as a data location.
   * Copy `example_profile.csv` into it as `profile.csv`, then update it with your actual contact info.
   * Copy `example_experience.csv` into it as `experience.csv`, then populate it with your tabular work history.

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

# Generate a complete Master Resume without tailoring to a specific job (skips cover letter)
hatch run generate -- --master
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

Each run prints its run directory (see plan §3.1 for where run directories live). Your freshly deployed `[Company]_[Role]_Resume_[Initials].docx` and `[Company]_[Role]_CoverLetter_[Initials].docx` are in it.

## Interpreting ATS Validation Output

When running the engine with the `--validate` flag, a secondary review pass generates an
`[Company]_[Role]_ats_[Initials].txt` file containing ATS scoring metrics. Here is how to
interpret the results:

* **Score (X/100):** A general alignment score indicating how well your generated resume matches
  the core requirements of the job requisition. Aim for 80+.
* **Missing Keywords:** A list of critical hard skills or technologies explicitly mentioned in
  the job description that were not found or successfully injected into the resume.
* **Formatting Compliance:** Feedback on structural readability (e.g., whether the layout is
  too dense or lacks proper sectioning).
* **Critical Feedback:** Actionable, high-level advice from the AI on how to manually tweak
  the generated document before submission (e.g., "Add more metrics to your Acme Corp role").

## Interpreting Job Desirability Output

When running the engine with the `--score-job` flag, an additional review pass generates a
`[Company]_[Role]_desirability_[Initials].txt` file containing an evaluation of the role against
your personal preferences. Here is how to interpret the results:

* **Overall Score (X/100):** A general metric indicating how well the job aligns with your
  configured preferences (e.g., minimum salary, remote status).
* **Remote & Salary Alignment:** A qualitative breakdown of whether the job meets, exceeds, or
  falls short of your baseline compensation and location requirements.
* **Benefits Analysis:** An evaluation of the company's stated benefits compared to your
  target benefits profile.
* **Pros & Cons:** An actionable list of advantages and potential red flags identified by the AI
  based on the job description and your preferences.

## Development Commands

For developers validating changes or contributing to the repository, workspace checks are exposed natively via Hatch:

```bash
hatch run test    # Run unit testing suite via pytest
hatch run lint    # Validate style and security rules via ruff check
hatch run format  # Apply automated codebase formatting via ruff format
```

Contributor conventions (commits, branches, the no-fabrication rules) are in [CLAUDE.md](CLAUDE.md).

## Project Structure

```text
resume-optimizer/
├── .github/
│   ├── dependabot.yml       # Dependency tracking configuration
│   └── workflows/           # GitHub Actions workflows
├── src/
│   └── resume_optimizer/
│       ├── prompts/         # Packaged prompts
│       └── templates/       # Packaged Jinja2 layouts
├── tests/                   # Complete unit test suite
├── resume_reference.docx    # Your MS Word styles document for Pandoc (git-ignored; supply it)
├── tune_template.py         # Utility script for tuning MS Word outputs locally
├── dummy_gemini_output.json # Mock AI data payload used by tune_template.py
├── pyproject.toml           # Declarative tool settings, dependencies, and metadata
└── .pre-commit-config.yaml  # Local Git compliance commit hook mapping
```
