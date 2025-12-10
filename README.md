# Autonomous FNOL Claims Processing Agent

**GitHub Repository:** [ Repository Link Here]([https://github.com/yourusername/fnol-claims-agent](https://github.com/Sreejareddy2208/fnol-claims-agent))

> Replace the GitHub link above with your actual repository URL after pushing the code.

---

## Overview

A lightweight Python agent that processes First Notice of Loss (FNOL) documents to:
- Extract key fields from PDF/TXT files
- Identify missing mandatory fields
- Classify and route claims to appropriate workflows
- Provide routing explanations

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Usage

**Command Line:**
```bash
# Process a single file
python fnol_agent.py --input samples/fnol_auto.txt --pretty

# Process all files in a directory
python fnol_agent.py --input samples --pretty
```

**Web Interface:**
```bash
python app.py
```
Then open `http://localhost:5000` in your browser.

---

## Approach

### Field Extraction
- Uses regex patterns to extract fields from structured FNOL documents
- Supports PDF (via pypdf) and plain text files
- Extracts: policy info, incident details, parties, assets, estimates

### Routing Rules (Priority Order)
1. **Manual Review** - If any mandatory field is missing
2. **Investigation** - If description contains fraud keywords (fraud, inconsistent, staged, suspicious)
3. **Specialist Queue** - If claim type is "injury"
4. **Fast-track** - If estimated damage < $25,000
5. **Standard Review** - Default route

### Features
- Negation detection for fraud keywords (e.g., "No fraud" is ignored)
- Inconsistency detection (flags when initial estimate is far below estimated damage)
- Web interface with drag-and-drop file upload
- JSON output format

---

## Output Format

```json
{
  "file": "samples/fnol_auto.txt",
  "extractedFields": {
    "policy_number": "POL-123456",
    "policyholder_name": "John Doe",
    "incident_date": "12/05/2025",
    "estimated_damage": 12500.0,
    ...
  },
  "missingFields": [],
  "recommendedRoute": "Fast-track",
  "reasoning": "Estimated damage 12500.0 < 25000"
}
```

---

## Mandatory Fields

These fields are checked for completeness:
- `policy_number`, `policyholder_name`, `incident_date`, `incident_description`
- `claim_type`, `estimated_damage`, `attachments`, `initial_estimate`

---

## Project Structure

```
fnol-claims-agent/
├── fnol_agent.py          # Core processing logic
├── app.py                 # Flask web application
├── requirements.txt       # Dependencies
├── templates/
│   └── index.html         # Web frontend
└── samples/               # Sample FNOL documents
    ├── fnol_auto.txt
    ├── fnol_injury.txt
    └── fnol_missing.txt
```

---

## AI-Assisted Development

This project was developed with AI assistance (Cursor AI) to accelerate:
- Code generation and refactoring
- Web interface development
- Documentation writing
- Pattern design for field extraction

All code was reviewed and tested manually. Business logic and routing rules were designed by the developer.

---

## Testing

Sample documents are provided in `samples/` directory. Run:
```bash
python fnol_agent.py --input samples --pretty
```

---

## Notes

- PDF parsing requires text-based PDFs (not scanned images)
- Field extraction works best with consistently formatted documents
- Regex patterns handle common FNOL document variations

---

## License

Created for assessment purposes.
