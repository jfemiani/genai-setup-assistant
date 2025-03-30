# Lab 0: GenAI Development Environment Assistant

This tool is an interactive assistant to guide students through setting up their Python development environment for **CSE 4/534: Generative AI**.

**Live App:** https://genai-dev-setup-assistant.streamlit.app/

---

## What It Does

The assistant walks you through:

- Installing Python and either Anaconda or Miniforge
- Creating a `conda` environment with required packages
- Installing tools like Pandoc, LaTeX (via `tectonic`), and VS Code extensions
- Troubleshooting any issues during setup
- Producing a Markdown report (`my_dev_setup.md`) and exporting it as a PDF

---

## Requirements

To use the assistant, you will need:

- A web browser
- An [OpenAI API key](https://platform.openai.com/account/api-keys)

Your API key is used only in your session and is not stored or transmitted by the app.

---

## How to Use

1. Visit the link above.
2. Paste your OpenAI API key when prompted.
3. Follow the step-by-step setup instructions.
4. If anything fails, the assistant will help you debug and continue.
5. After setup, generate and submit your environment report.

---

## Technical Notes

This app is built with:

- Streamlit
- The OpenAI Python SDK
- A structured system prompt tailored to the Lab 0 objectives

It is deployed publicly on Streamlit Cloud for educational use in this course.

---

## Questions?

Please post in the course discussion forum or contact your instructor or TA.
