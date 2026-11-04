"""Shipped word lists for the deterministic output checks (plan §3.4, §3.10).

These are static starting points. D4 extends and calibrates the AI-tell list, and C-series work
replaces the general vocabulary with the ledger's own skills file. Everything is lower-case.
"""

# Terms that read as concrete, checkable claims about tools, platforms and methods. A term from
# this list that appears in the output but nowhere in the candidate's data is reported.
GENERAL_VOCABULARY: frozenset[str] = frozenset(
    {
        # languages
        "python", "java", "javascript", "typescript", "c++", "c#", "golang", "rust", "ruby",
        "php", "scala", "kotlin", "swift", "bash", "powershell", "perl", "sql", "r",
        # cloud and infrastructure
        "aws", "azure", "gcp", "google cloud", "kubernetes", "docker", "terraform", "ansible",
        "puppet", "chef", "cloudformation", "helm", "openshift", "vmware", "linux", "unix",
        "windows server", "nginx", "apache", "lambda", "ec2", "s3", "eks", "ecs", "rds",
        "dynamodb", "cloudwatch", "iam", "vpc",
        # delivery and tooling
        "jenkins", "github actions", "gitlab", "gitlab ci", "circleci", "argocd", "git",
        "jira", "confluence", "servicenow", "ci/cd", "devops", "devsecops", "sre", "gitops",
        # data and ml
        "postgresql", "postgres", "mysql", "mongodb", "redis", "kafka", "spark", "hadoop",
        "snowflake", "databricks", "airflow", "tableau", "power bi", "elasticsearch", "splunk",
        "datadog", "prometheus", "grafana", "pandas", "numpy", "tensorflow", "pytorch",
        "machine learning", "deep learning", "data science", "data engineering", "etl",
        # web and apis
        "react", "angular", "vue", "node.js", "django", "flask", "fastapi", "spring", "graphql",
        "rest", "grpc", "microservices", "serverless",
        # security and compliance
        "soc 2", "iso 27001", "hipaa", "pci", "pci dss", "gdpr", "fedramp", "nist", "owasp",
        "zero trust", "siem", "oauth", "saml",
        # practices
        "agile", "scrum", "kanban", "safe", "itil", "six sigma", "tdd", "okr",
        # certifications
        "pmp", "cissp", "cism", "ccna", "ccnp", "cka", "ckad", "csm",
    }
)  # fmt: skip

# Vocabulary entries that are also ordinary English words. They match only in this exact form,
# so "react to feedback", "the rest of the team" and "R&D" are not read as tool claims.
CASE_SENSITIVE_TERMS: dict[str, str] = {
    "r": "R", "safe": "SAFe", "rest": "REST", "react": "React", "spring": "Spring",
    "chef": "Chef", "puppet": "Puppet", "swift": "Swift", "rust": "Rust", "lambda": "Lambda",
    "spark": "Spark", "helm": "Helm",
}  # fmt: skip

# Words that signal seniority. An unsupported one is a title or scope inflation risk.
LEVEL_WORDS: frozenset[str] = frozenset(
    {
        "director", "head", "lead", "principal", "staff", "senior", "manager", "chief", "vp",
        "president", "executive", "founder", "owner", "supervisor",
    }
)  # fmt: skip

# Nouns that make a preceding level word read as a job title ("senior manager of ...").
FUNCTION_NOUNS: frozenset[str] = frozenset(
    {
        "manager", "director", "engineer", "architect", "developer", "analyst", "consultant",
        "officer", "administrator", "specialist", "scientist", "designer", "technician",
        "strategist", "programmer", "coordinator",
    }
)  # fmt: skip

# Verbs and structure words that resume prose capitalises legitimately (leading a bullet, after a
# colon). A capitalised token in this list is never reported (plan §3.10 verb-and-structure list).
VERB_LEXICON: frozenset[str] = frozenset(
    {
        "accelerated", "achieved", "administered", "advised", "analyzed", "analysed",
        "architected", "authored", "automated", "built", "championed", "collaborated",
        "configured", "consolidated", "coordinated", "created", "cut", "decreased", "defined",
        "delivered", "deployed", "designed", "developed", "directed", "drove", "enabled",
        "engineered", "enhanced", "established", "evaluated", "executed", "expanded",
        "facilitated", "guided", "identified", "implemented", "improved", "increased",
        "integrated", "introduced", "launched", "led", "maintained", "managed", "mentored",
        "migrated", "modernized", "monitored", "negotiated", "optimized", "orchestrated",
        "oversaw", "partnered", "planned", "produced", "provided", "reduced", "refactored",
        "replaced", "resolved", "restructured", "reviewed", "scaled", "secured", "shipped",
        "simplified", "standardized", "streamlined", "supported", "trained", "transformed",
        "upgraded", "wrote",
        "and", "the", "for", "with", "to", "of", "in", "on", "at", "by", "as", "a", "an",
        "i", "i'm", "i've", "my", "our", "we", "dear", "sincerely", "regards", "thank", "thanks",
    }
)  # fmt: skip

MONTHS: frozenset[str] = frozenset(
    {
        "january", "february", "march", "april", "may", "june", "july", "august", "september",
        "october", "november", "december", "jan", "feb", "mar", "apr", "jun", "jul", "aug",
        "sep", "sept", "oct", "nov", "dec", "present",
    }
)  # fmt: skip

# Static AI-tell phrases (plan §3.4). Matched case-insensitively as whole words or phrases.
# D4 extends and calibrates this list; until then it only counts, and never blocks.
AI_TELL_PHRASES: tuple[str, ...] = (
    "results-driven",
    "dynamic professional",
    "passionate about",
    "passion for",
    "proven track record",
    "track record of success",
    "detail-oriented",
    "highly motivated",
    "self-starter",
    "team player",
    "go-getter",
    "think outside the box",
    "spearheaded",
    "leveraging",
    "leveraged",
    "robust",
    "cutting-edge",
    "synergy",
    "seamlessly",
    "fast-paced",
    "ever-evolving",
    "demonstrated ability",
    "i am excited to",
    "i am writing to express",
    "i am thrilled",
    "thrive in",
    "unique blend",
    "testament to",
    "delve",
    "tapestry",
    "navigate the complexities",
    "in today's",
)
