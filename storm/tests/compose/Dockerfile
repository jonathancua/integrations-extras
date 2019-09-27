FROM maven:3.5.0-jdk-7

RUN curl -fsSL http://mirror.cc.columbia.edu/pub/software/apache/storm/apache-storm-1.2.3/apache-storm-1.2.3.tar.gz -o storm.tar.gz \
    && tar -xf storm.tar.gz \
    && mv ./apache* storm \
    && cd storm/examples/storm-starter \
    && mvn package \
    && mv target/storm-starter-*.jar /topology.jar

ENTRYPOINT ["/bin/sleep"]
CMD ["120"]
