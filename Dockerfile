# docker build -t my-flask-api .
# docker run -p 5000:5000 my-flask-api


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
ENV FLASK_RUN_HOST=0.0.0.0

# command to run the flask app
CMD ["flask", "run"]
