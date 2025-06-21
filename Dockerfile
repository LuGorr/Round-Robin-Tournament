FROM python:3.11-slim

RUN apt-get update && apt-get install -y wget unzip && \
    wget https://github.com/MiniZinc/MiniZincIDE/releases/download/2.7.5/MiniZincIDE-2.7.5-bundle-linux-x86_64.tgz && \
    tar -xzf MiniZincIDE-2.7.5-bundle-linux-x86_64.tgz && \
    mv MiniZincIDE-2.7.5-bundle-linux-x86_64 /opt/minizinc && \
    ln -s /opt/minizinc/bin/minizinc /usr/local/bin/minizinc && \
    rm MiniZincIDE-2.7.5-bundle-linux-x86_64.tgz && \
    apt-get clean

RUN pip install z3-solver

WORKDIR /app

COPY SMT/SMT.py /SMT/SMT.py
#COPY CP/CP.mzn /CP/CP.mzn
#COPY MIP/* /MIP/*

COPY SMT/run_smt.sh /SMT/run_smt.sh
#COPY CP/run_cp.sh /CP/run_cp.sh

RUN chmod +x /SMT/run_smt.sh /CP/run_cp.sh

VOLUME ["/res"]

ENV PYTHONUNBUFFERED=1

CMD ["/SMT/run_smt.sh"]
#CMD ["/CP/run_cp.sh"]