#!/bin/bash
set -eo pipefail

# install nodeos locally
LEAP_VERSION="${1}"
ORCH_IP="${2}"
PORT="${3}"
OS="ubuntu22.04"

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
else
  BRANCH="${LEAP_VERSION}"
  response_json=$(curl -H 'Accept: application/json' http://${ORCH_IP}:${PORT:-4000}/deb_download_url?branch="${BRANCH}")
  CHECK=$(echo $response_json | jq .success | sed 's/"//g' )
  if [ "$CHECK" == "true" ]; then
    URL=$(echo $response_json | jq .url | sed 's/"//g' )
    source ~/token.env
    curl -L -o download.zip -H 'Accept: application/vnd.github+json' -H 'X-GitHub-Api-Version: 2022-11-28' -H "Authorization: Bearer ${TOKEN}" "$URL"
  else
    # didn't get valid URL to download artifact bad token or maybe artifact no longer exists
    exit 127
  fi
fi

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

## root setup ##
# clean out un-needed files
for not_needed_deb_file in "${HOME:?}"/leap_*.deb; do
    if [ "${not_needed_deb_file}" != "${HOME:?}/${DEB_FILE}" ]; then
        echo "Removing not needed deb ${not_needed_deb_file}"
        rm -rf "${not_needed_deb_file}"
    fi
done

# download file if needed
if [ ! -f "${HOME:?}/${DEB_FILE}" ]; then
    wget --directory-prefix="${HOME}" "${DEB_URL}" 2> /dev/null
fi

# install nodeos locally
echo "Installing nodeos ${LEAP_VERSION} locally"
[ -d "${HOME:?}/nodeos" ] && rm -rf "${HOME:?}/nodeos"
mkdir "${HOME:?}/nodeos"
dpkg -x "${HOME:?}/${DEB_FILE}" "${HOME:?}/nodeos"

echo "Done. - ${BASH_SOURCE[0]}"
