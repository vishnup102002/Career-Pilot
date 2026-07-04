FROM python:3.11-bullseye
ENV PYTHONUNBUFFERED=1
WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install-deps chromium

RUN useradd -m -u 1000 user
ENV PLAYWRIGHT_BROWSERS_PATH=/home/user/.cache/ms-playwright

# Create /data for persistent storage BEFORE switching to non-root user
RUN mkdir -p /data && chown user:user /data
VOLUME /data

USER user
ENV PATH="/home/user/.local/bin:$PATH"
RUN playwright install chromium
COPY --chown=user . /code

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
