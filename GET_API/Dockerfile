# docker build -t chatbot .
# docker run -p 5000:5000 chatbot

#now on 5002
# use the official python slim image as the base image
FROM python:3.9-slim

# set the working directory in the container
WORKDIR /app

# copy the requirements file to the container
COPY requirements.txt .

# install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of the application files to the container
COPY . .

# expose the port on which the app runs
EXPOSE 5000

# set the environment variable for flask
ENV FLASK_APP=app.py


# command to run the flask app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
