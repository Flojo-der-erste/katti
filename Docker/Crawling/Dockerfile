#https://github.com/SeleniumHQ/docker-selenium

FROM python:3.10-bullseye AS builder


RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install wget
RUN apt-get install software-properties-common -y
RUN apt-get -y install xvfb

RUN useradd drwho_docker -m
USER drwho_docker

RUN mkdir -p /home/drwho_docker/selenium_logs
RUN mkdir -p /home/drwho_docker/plugins
RUN mkdir -p /home/drwho_docker/downloads
RUN mkdir -p /home/drwho_docker/init_browser_profile

USER root

FROM builder AS build_chromium

RUN apt-get -y install chromium
RUN chromium --version

#https://chromedriver.storage.googleapis.com/index.html?path=109.0.5414.74/
FROM build_chromium as build_google


ARG CHROME_VERSION="google-chrome-stable"
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update -qqy \
  && apt-get -qqy install \
    ${CHROME_VERSION:-google-chrome-stable} \
  && rm /etc/apt/sources.list.d/google-chrome.list \
  && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

RUN google-chrome --version
ARG CHROME_DRIVER_VERSION
RUN wget --no-verbose -O /tmp/chromedriver_linux64.zip https://chromedriver.storage.googleapis.com/109.0.5414.74/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver_linux64.zip -d /home/drwho_docker/ \
    && chmod 755 /home/drwho_docker/chromedriver / \
    && rm /tmp/chromedriver_linux64.zip



FROM build_google AS build_edge
ARG EDGE_VERSION="microsoft-edge-stable"
RUN wget -q -O - https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
  && echo "deb https://packages.microsoft.com/repos/edge stable main" >> /etc/apt/sources.list.d/microsoft-edge.list \
  && apt-get update -qqy \
  && apt-get -qqy install ${EDGE_VERSION} \
  && rm /etc/apt/sources.list.d/microsoft-edge.list \
  && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

#https://msedgedriver.azureedge.net/109.0.1518.52/edgedriver_linux64.zip
ARG EDGE_DRIVER_VERSION
RUN if [ -z "$EDGE_DRIVER_VERSION" ]; \
  then EDGE_MAJOR_VERSION=$(microsoft-edge --version | sed -E "s/.* ([0-9]+)(\.[0-9]+){3}.*/\1/") \
    && EDGE_DRIVER_VERSION=$(wget --no-verbose -O - "https://msedgedriver.azureedge.net/LATEST_RELEASE_${EDGE_MAJOR_VERSION}_LINUX" | tr -cd "\11\12\15\40-\176" | tr -d "\r"); \
  fi \
  && wget --no-verbose -O /tmp/msedgedriver_linux64.zip https://msedgedriver.azureedge.net/$EDGE_DRIVER_VERSION/edgedriver_linux64.zip \
    && unzip /tmp/msedgedriver_linux64.zip -d /home/drwho_docker/ \
    && chmod 755 /home/drwho_docker/msedgedriver / \
    && rm /tmp/msedgedriver_linux64.zip


FROM build_edge AS build_firefox
ARG FIREFOX_VERSION=latest
RUN FIREFOX_DOWNLOAD_URL=$(if [ $FIREFOX_VERSION = "latest" ] || [ $FIREFOX_VERSION = "beta-latest" ] || [ $FIREFOX_VERSION = "nightly-latest" ] || [ $FIREFOX_VERSION = "devedition-latest" ] || [ $FIREFOX_VERSION = "esr-latest" ]; then echo "https://download.mozilla.org/?product=firefox-$FIREFOX_VERSION-ssl&os=linux64&lang=en-US"; else echo "https://download-installer.cdn.mozilla.net/pub/firefox/releases/$FIREFOX_VERSION/linux-x86_64/en-US/firefox-$FIREFOX_VERSION.tar.bz2"; fi) \
  && apt-get update -qqy \
  && apt-get -qqy --no-install-recommends install libavcodec-extra \
  && rm -rf /var/lib/apt/lists/* /var/cache/apt/* \
  && wget --no-verbose -O /tmp/firefox.tar.bz2 $FIREFOX_DOWNLOAD_URL \
  && rm -rf /opt/firefox \
  && tar -C /opt -xjf /tmp/firefox.tar.bz2 \
  && rm /tmp/firefox.tar.bz2 \
  && mv /opt/firefox /opt/firefox-$FIREFOX_VERSION \
  && ln -fs /opt/firefox-$FIREFOX_VERSION/firefox /usr/bin/firefox

#============
# GeckoDriver
#============
ARG GECKODRIVER_VERSION=latest
RUN GK_VERSION=$(if [ ${GECKODRIVER_VERSION:-latest} = "latest" ]; then echo "0.32.0"; else echo $GECKODRIVER_VERSION; fi) \
  && echo "Using GeckoDriver version: "$GK_VERSION \
  && wget --no-verbose -O /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v$GK_VERSION/geckodriver-v$GK_VERSION-linux64.tar.gz \
  && tar -C /opt -zxf /tmp/geckodriver.tar.gz \
  && rm /tmp/geckodriver.tar.gz \
  && mv /opt/geckodriver /home/drwho_docker/geckodriver

RUN apt-get update && apt-get install -y wget bzip2 libxtst6 libgtk-3-0 libx11-xcb-dev libdbus-glib-1-2 libxt6 libpci-dev && rm -rf /var/lib/apt/lists/*
FROM build_firefox AS build_katti
RUN apt-get update


WORKDIR /home/drwho_docker
RUN chown drwho_docker:drwho_docker /home/drwho_docker
USER drwho_docker

COPY --chown=drwho_docker:drwho_docker /source_code source_code/
COPY --chown=drwho_docker:drwho_docker /Docker/Crawling/idontcareaboutcookies_chrome.crx idontcareaboutcookies_chrome.crx
COPY --chown=drwho_docker:drwho_docker Docker/Crawling/katti_surv_chrome.crx katti_surv_chrome.crx
COPY --chown=drwho_docker:drwho_docker Docker/Crawling/katti_surv_chrome.xpi katti_surv_chrome.xpi
COPY --chown=drwho_docker:drwho_docker Docker/Crawling/idontcareaboutcookies.xpi idontcareaboutcookies.xpi


WORKDIR /home/drwho_docker/source_code
RUN pip  install --user -r /home/drwho_docker/source_code/requirements
RUN python3.10 /home/drwho_docker/source_code/setup.py install --user
WORKDIR /home/drwho_docker
ENTRYPOINT ["python", "/home/drwho_docker/source_code/Crawling/DockerCode/start_script.py"]

