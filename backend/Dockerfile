FROM python:3.11
WORKDIR /backend
COPY requirements-additions.txt .
RUN pip install --no-cache-dir -r requirements-additions.txt
COPY . .
