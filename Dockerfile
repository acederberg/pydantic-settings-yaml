FROM python:3.10


WORKDIR "/home/runner/app/"
RUN useradd -d "/home/runner/" dev \
	&& chown "dev:dev" "/home/runner/"
USER "dev"
COPY requirements.* .
RUN find requirements.* | xargs -i pip install -r {}
RUN echo 'source "/home/runner/app/.devrc"' >> ~/.bashrc

ENTRYPOINT "bash"

