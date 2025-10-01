FROM python:3.11-slim

RUN pip install z3-solver amplpy pandas

ARG MINIZINC_VERSION=2.9.2

RUN apt-get update && apt-get install -y wget unzip bc jq libgl1-mesa-dev libfontconfig1 && \
    wget https://github.com/MiniZinc/MiniZincIDE/releases/download/${MINIZINC_VERSION}/MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-x86_64.tgz && \
    tar -xzf MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-x86_64.tgz && \
    mv MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-x86_64 /opt/minizinc && \
    ln -s /opt/minizinc/bin/minizinc /usr/local/bin/minizinc && \
    rm MiniZincIDE-${MINIZINC_VERSION}-bundle-linux-x86_64.tgz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Imposta il PATH per gli eseguibili di MiniZinc (permanente)
ENV MINIZINC_BUNDLE_PATH="/opt/minizinc"
ENV PATH="${PATH}:/opt/minizinc/bin"

# Imposta LD_LIBRARY_PATH per le librerie di MiniZinc/OR-Tools (permanente)
# Questo è il passaggio chiave per risolvere l'errore libabsl_flags_parse.so
ENV LD_LIBRARY_PATH="${MINIZINC_BUNDLE_PATH}/lib"

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
    python3.11 -m amplpy.modules activate "${AMPL_LICENSE_UUID}"

# Since these are CMD and not ENTRYPOINT, they will be overridden if the container is run with a different command.
CMD ["/bin/bash", "-c", "/app/SMT/run_smt.sh && /app/CP/run_cp.sh && /app/MIP/run_mip.sh"]