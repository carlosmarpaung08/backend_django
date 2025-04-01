FROM python:3.10

WORKDIR /app

# Instal dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn

# Salin kode proyek
COPY . .

# Variabel lingkungan
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Perintah untuk menjalankan aplikasi
CMD ["python", "-m", "gunicorn", "backend_phyton.wsgi", "--bind", "0.0.0.0:8000"]