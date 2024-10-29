#!/bin/bash
set -eo pipefail

# install nodeos locally
LEAP_VERSION="${1}"
ORCH_IP="${2}"
PORT="${3}"
OS="ubuntu22.04"

## root setup ##
# clean out un-needed files
for not_needed_deb_file in "${HOME:?}"/*_*.deb; do
  echo "Removing not needed deb ${not_needed_deb_file}"
  rm -rf "${not_needed_deb_file}"
done

# is this an official release version number
# or a branch
if [[ "$LEAP_VERSION" =~ ^v?[1-9]\.[0-9]\.[0-9]$ ]]; then
  LEAP_VERSION="${LEAP_VERSION#v}"
  if [[ "${LEAP_VERSION:0:1}" == '4' ]]; then
    DEB_FILE="leap_${LEAP_VERSION}-${OS}_amd64.deb"
    DEB_URL="https://github.com/AntelopeIO/leap/releases/download/v${LEAP_VERSION}/${DEB_FILE}"
  elif [[ "${LEAP_VERSION:0:1}" == '5' ]]; then
    DEB_FILE="leap_${LEAP_VERSION}_amd64.deb"
    DEB_URL="https://github.com/AntelopeIO/leap/releases/download/v${LEAP_VERSION}/${DEB_FILE}"
  else  # spring
    DEB_FILE="antelope-spring_${LEAP_VERSION}_amd64.deb"
    DEB_URL="https://github.com/AntelopeIO/spring/releases/download/v${LEAP_VERSION}/${DEB_FILE}"
  fi
  # download file if needed
  wget --directory-prefix="${HOME}" "${DEB_URL}" 2> /dev/null
else
  BRANCH="${LEAP_VERSION}"
  response_json=$(curl -H 'Accept: application/json' http://${ORCH_IP}:${PORT:-4000}/deb_download_url?branch="${BRANCH}")
  CHECK=$(echo $response_json | jq .success | sed 's/"//g' )
  if [ "$CHECK" == "true" ]; then
    URL=$(echo $response_json | jq .url | sed 's/"//g' )
    source ${HOME:?}/token.env
    # download artifact from debian
    for ((i=1; i<=8; i++)); do
      http_status=$(curl -L -s -w "%{http_code}" -o ${HOME:?}/download.zip -H 'Accept: application/vnd.github+json' -H 'X-GitHub-Api-Version: 2022-11-28' -H "Authorization: Bearer ${TOKEN}" "$URL")
      if [ "$http_status" -eq 200 ]; then
        break
      fi
      # If we haven't reached the last attempt, wait for a bit before retrying
      if [ "$i" -lt 8 ]; then
        sleep 2  # Wait 2 seconds before retrying
      fi
    done
    cd $HOME || exit 127
    unzip ${HOME:?}/download.zip
  else
    # didn't get valid URL to download artifact bad token or maybe artifact no longer exists
    exit 127
  fi
fi

DEB_FILE=$(ls -1 $HOME/*_*.deb | head -1)

## dry-run
[[ "$(echo "$3" | grep -icP '^DRY(-_)>RUN$')" == '1' ]] && export DRY_RUN='true'
if [[ "${DRY_RUN}" == 'true' ]]; then
    prinf "\e[1;33mWARNING: DRY-RUN is set!\e[0m\n"
    echo "LEAP_VERSION='${LEAP_VERSION}'"
    echo "OS='${OS}'"
    echo "DEB_FILE='${DEB_FILE}'"
    echo "DEB_URL='${DEB_URL}'"
    echo "Exiting... - ${BASH_SOURCE[0]}"
    exit 0
fi

# install nodeos locally
echo "Installing nodeos ${LEAP_VERSION} locally"
[ -d "${HOME:?}/nodeos" ] && rm -rf "${HOME:?}/nodeos"
mkdir "${HOME:?}/nodeos"
dpkg -x "${DEB_FILE}" "${HOME:?}/nodeos"

echo "Done. - ${BASH_SOURCE[0]}"
