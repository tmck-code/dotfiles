#!/bin/bash

# Fixing some OSX bs. -------------------------------------
alias ls='ls -G'
alias shuf="gshuf"
alias python="python3"
alias pip="pip3"

# Git aliases ---------------------------------------------

alias branch='git rev-parse --abbrev-ref HEAD'
alias git="hub"

function git_branch() {
  local branch
  if branch=$(git rev-parse --abbrev-ref HEAD 2> /dev/null); then
    if [[ "$branch" == "HEAD" ]]; then
      branch='detached*'
    fi
    git_branch="  ($branch):  "
  else
    git_branch=""
  fi
  echo $git_branch
}

# Docker aliases ------------------------------------------

alias dgc="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v /etc:/etc -e FORCE_IMAGE_REMOVAL=1 spotify/docker-gc"
alias dls="docker network ls && docker ps -a && docker images"
alias db="docker build -t ${PWD##*/} -f ops/Dockerfile ."
alias container="docker images -q $1"

alias docker_stop_containers="docker ps -aq | xargs docker stop"
alias docker_remove_containers="docker ps -aq | xargs docker rm"
alias docker_purge_containers="docker_stop_containers && docker_remove_containers"

alias docker_ls_empty_images="docker images | grep '<none>' | sed -E 's/ +/,/g' | cut -d ',' -f 3"
alias docker_remove_empty_images="docker_ls_empty_images | xargs docker rmi"

alias docker_cleanup="docker_remove_empty_images && docker_purge_containers && dgc"

alias dexec="docker exec $(container $1) -it bash"
alias drun_id="docker run -it 65298f9201fa bash"

