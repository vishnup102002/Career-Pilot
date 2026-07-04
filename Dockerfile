FROM python:3.11-bullseye
WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install-deps chromium

RUN useradd -m -u 1000 user
ENV PLAYWRIGHT_BROWSERS_PATH=/home/user/.cache/ms-playwright

USER user
ENV PATH="/home/user/.local/bin:$PATH"
RUN playwright install chromium
COPY --chown=user . /code

# Persistent storage for SQLite DB on HF Spaces
# Enable in Space Settings > Storage > Persistent Storage
RUN mkdir -p /data && chown user:user /data
VOLUME /data

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
