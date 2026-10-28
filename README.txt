JOANNE'S NAIL TRY-ON CONNECTION — STARTER FILES

These files are a starter connection for a Render web service. They do NOT change your existing website by themselves.

IMPORTANT
- Never put your Perfect Corp API key in the HTML or GitHub repository.
- Add it only in Render's private Environment settings under the name PERFECT_CORP_API_KEY.
- This service uses Perfect Corp's documented AI Nail Virtual Try-On workflow. It has not been tested with your account/API key, so we must test it before connecting the live website.
- Perfect Corp may require a particular file-upload response format, API plan/credits, or effect configuration. If it returns an error, do not share your API key; share only the error message.

FILES
- app.py: small private server that accepts a photo and colour, uploads the photo to Perfect Corp, starts the nail try-on task, and waits for the result.
- requirements.txt: packages needed to run it.
- render.yaml: deployment settings for Render.

NEXT STEPS (when ready)
1. Sign in to Render and choose New > Blueprint, then connect the GitHub repository containing these files (or upload the files into a new private/public repo as needed).
2. When asked for PERFECT_CORP_API_KEY, enter the key privately in Render. Never put the key into a file.
3. Wait for deployment. Open the service URL; it should display JSON showing service and whether it is ready.
4. Only after the service works should the website HTML be updated to send photos to its /api/try-on endpoint.

This is a starter, not a verified production integration. The result URL parsing and upload response fields may need adjustment based on the exact response from your Perfect Corp account.
