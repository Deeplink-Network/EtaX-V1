FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the files from the src directory to the app directory in the container
COPY src/ .

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "server:main()"]