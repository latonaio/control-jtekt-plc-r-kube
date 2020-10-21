FROM latonaio/l4t:latest

ENV POSITION=Runtime \
    SERVICE=control-jtekt-plc-r \
    AION_HOME="/var/lib/aion" \
    CONFIG="${AION_HOME}/Data/${SERVICE}_1"

RUN mkdir ${AION_HOME}
RUN mkdir -p ${CONFIG}

# Setup Directoties
RUN mkdir -p ${AION_HOME}/$POSITION/$SERVICE
WORKDIR ${AION_HOME}/$POSITION/$SERVICE/

ADD . .
#RUN cp ./data/command_list.json ${CONFIG} && cp ./data/trigger_list.json ${CONFIG}
RUN python3 setup.py install
CMD ["python3", "-m", "plc_data"]
# ENTRYPOINT ["/bin/sh", "-c", "while :; do sleep 10; done"]
