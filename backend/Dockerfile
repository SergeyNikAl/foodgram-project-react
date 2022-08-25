FROM python:3.7-slim

WORKDIR backend/

COPY . .

RUN pip install -r backend/reuirements.txt --no-cache-dir

CMD ["gunicorn", "foodrgam.wsgi:application", "--build", "0:8000"]