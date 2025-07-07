FROM python:3.11-slim

RUN apt-get update && apt-get install -y wget unzip bc jq && \
    wget https://github.com/MiniZinc/MiniZincIDE/releases/download/2.7.5/MiniZincIDE-2.7.5-bundle-linux-x86_64.tgz && \
    tar -xzf MiniZincIDE-2.7.5-bundle-linux-x86_64.tgz && \
    mv MiniZincIDE-2.7.5-bundle-linux-x86_64 /opt/minizinc && \
    ln -s /opt/minizinc/bin/minizinc /usr/local/bin/minizinc && \
    rm MiniZincIDE-2.7.5-bundle-linux-x86_64.tgz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install z3-solver

WORKDIR /app

RUN mkdir -p /app/SMT /app/CP /app/MIP

COPY ./SMT /app/SMT
COPY ./CP /app/CP
#COPY ./CP/run_cp.sh ./CP/run_cp.sh
#COPY ./MIP/* /app/MIP/*

RUN chmod +x /app/SMT/run_smt.sh
RUN chmod +x /app/CP/run_cp.sh
#/app/CP/CP.sh /app/MIP/MIP.sh

VOLUME ["/res"]

ENV PYTHONUNBUFFERED=1

CMD ["/bin/bash", "/app/SMT/run_smt.sh"]
CMD ["/bin/bash", "/app/CP/run_cp.sh"]
#ENTRYPOINT ["/bin/bash", "-c", "/app/SMT/SMT.sh && /app/CP/CP.sh && /app/MIP/MIP.sh"]