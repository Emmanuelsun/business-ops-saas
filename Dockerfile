# Lumen: the recipe for the app's container.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Install the libraries first, so Docker can reuse this step when only code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend and the web pages. Secrets are never copied (see .dockerignore).
COPY app ./app
COPY web ./web

# Run as a normal user, not as root.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Hosts such as Render give the port in the PORT variable; locally it is 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

# End of file.