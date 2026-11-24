# Original MSL ONE source snapshot

Earlier application source preserved separately from the current integrated CVRM MVP in ../MSL_ONE. This folder retains the original Python/React implementation; no user interaction history, API keys, generated reports, or installed dependencies are included.

For the current maintained demo and setup instructions, use the repository root README. To inspect this earlier interface, install requirements.txt in a fresh Python virtual environment, run uvicorn api:app on port 8000, then install the frontend package dependencies and run its Vite dev command. Optional providers use your own backend .env file; see .env.example. This is an archived prototype and was not revalidated as a separate production service during upload.
