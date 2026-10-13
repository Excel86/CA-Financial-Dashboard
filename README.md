# CA Financial Dashboard — Deploy-Ready Starter

This is a deploy-ready Streamlit starter for a CA financial dashboard workshop.

## Run locally first

Install Python 3.10 or newer, open a terminal in this folder, then run:

```bash
python -m venv .venv
```

Windows: `.venv\Scripts\activate`

macOS/Linux: `source .venv/bin/activate`

Then run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publish a live URL using Streamlit Community Cloud

Publishing requires your own GitHub and Streamlit Community Cloud accounts. You must complete sign-in and authorization steps; this package cannot publish to those accounts automatically.

1. Sign in to GitHub and create a new repository.
2. Upload the files in this folder to the repository root: `app.py`, `requirements.txt`, `sample_financial_data.xlsx`, `prompt_library.md`, `manual_test_cases.md`, and `README.md`.
3. Sign in to https://share.streamlit.io/
4. Choose Create app / Deploy an app.
5. Select your GitHub repository, branch (usually `main`) and main file path `app.py`.
6. Deploy and wait for Streamlit to provide a URL.
7. Test upload, filters, calculations, exception rules and Excel export.

The Streamlit interface labels may change over time.

## Data and privacy
- The included workbook contains synthetic data for demonstration.
- Do not put confidential client data into a public repository.
- A public app may be accessible to anyone with its URL. Do not use real client data unless your firm has approved hosting, security, privacy and access controls.
- This prototype is not a production accounting, audit or tax system. Review calculations and results before professional use.

## Included files
- `app.py`: Streamlit dashboard
- `requirements.txt`: Python dependencies
- `sample_financial_data.xlsx`: synthetic example data
- `prompt_library.md`: AI prompts for building and modifying the app
- `manual_test_cases.md`: quick manual test cases
