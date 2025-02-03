FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Copy requirements.txt FIRST
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install system dependencies (if needed for your Python packages)
RUN apt-get update && apt-get install -y \
    python3-distutils \
    python3-dev \
    libpq-dev \
    build-essential \
    libffi-dev \
    zlib1g-dev \
    curl \
    gnupg\
    default-jdk \                            
    g++ \  
    nodejs \
    npm\                    
    && rm -rf /var/lib/apt/lists/*

# Install Node.js


# Install Yarn (optional, if needed for Node.js projects)
RUN npm install --global yarn



# Copy the rest of your Django project (AFTER installing npm dependencies)
COPY . .

# Create a non-root user and set it as the owner of the working directory
RUN adduser --disabled-password --gecos '' celeryuser \
    && chown -R celeryuser:celeryuser /app

# Switch to the celeryuser to avoid running as root
USER celeryuser

# Expose port
EXPOSE 8000

# Command to run Celery worker and Gunicorn
CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput  & gunicorn execute.wsgi:application --bind 0.0.0.0:$PORT"]