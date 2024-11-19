# docker build -t chatbot .
# docker run -p 5000:5000 chatbot

FROM continuumio/miniconda3:latest



WORKDIR /app

COPY requirements.txt .

RUN conda init bash && \
    /bin/bash -c "source ~/.bashrc && conda create -n chatbot_env python=3.9 -y" && \
    /bin/bash -c "source ~/.bashrc && conda activate chatbot_env && pip install --no-cache-dir -r requirements.txt"

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py

CMD ["/bin/bash", "-c", "source ~/.bashrc && conda activate chatbot_env && gunicorn -w 4 -b 0.0.0.0:5000 app:app"]
