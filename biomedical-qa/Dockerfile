FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip check
COPY pipeline.py test_pipeline.py ./
RUN python -m unittest -v
RUN useradd --create-home --uid 10001 app && mkdir /data && chown app:app /data
USER app
ENTRYPOINT ["python", "pipeline.py"]
CMD ["--help"]
