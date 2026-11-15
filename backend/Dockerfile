FROM python:3.12-slim

WORKDIR /app

# Cai dat thu vien
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Tao thu muc data cho metrics SQLite
RUN mkdir -p /app/data

EXPOSE 8000

# Chay FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
