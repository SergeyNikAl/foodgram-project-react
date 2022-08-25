FROM python:3.7-slim

WORKDIR backend/

COPY . .

RUN pip3 install -r reuirements.txt --no-cache-dir

CMD ["gunicorn", "foodrgam.wsgi:application", "--build", "0:8000"]