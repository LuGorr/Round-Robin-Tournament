FROM python:3.11-slim

RUN pip install z3-solver amplpy pandas

ARG MINIZINC_VERSION=2.9.2

RUN apt-get update && apt-get install -y wget unzip bc jq && \
    wget https://github.com/MiniZinc/MiniZincIDE/releases/download/${MINIZINC_VERSION}/MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-x86_64.tgz && \
    tar -xzf MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-x86_64.tgz && \
    mv MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-x86_64 /opt/minizinc && \
    ln -s /opt/minizinc/bin/minizinc /usr/local/bin/minizinc && \
    rm MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-x86_64.tgz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/SMT /app/CP /app/MIP

COPY ./SMT /app/SMT
COPY ./CP /app/CP
COPY ./MIP /app/MIP

RUN chmod +x /app/SMT/run_smt.sh
RUN chmod +x /app/CP/run_cp.sh
RUN chmod +x /app/MIP/run_mip.sh

VOLUME ["/res"]

ENV PYTHONUNBUFFERED=1

# Ideally, API codes should not be exposed like this
RUN python3.11 -m amplpy.modules install highs cbc gurobi cplex && \
    python3.11 -m amplpy.modules activate "caf71c55-8ecf-4310-90e3-f0195364ecce"

# Since these are CMD and not ENTRYPOINT, they will be overridden if the container is run with a different command.
CMD ["/bin/bash", "-c", "/app/SMT/run_smt.sh && /app/CP/run_cp.sh && /app/MIP/run_mip.sh"]