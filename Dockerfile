FROM minizinc/minizinc:latest

WORKDIR /app

COPY . .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        glpk-utils \
        coinor-cbc \
        build-essential \
        python3-tk && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# Set display variable for GUI (to work with X11)
ENV DISPLAY=:0

CMD ["python3", "main-tk.py"]
