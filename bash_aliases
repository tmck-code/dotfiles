# Fixing some OSX bs. -------------------------------------

alias db="docker build -t ${PWD##*/} -f Dockerfile ."

alias ls='ls -G'
alias shuf="gshuf"
alias python="python3"
alias pip="pip3"
alias tc="tmux-code"

# vm/utility commands -------------------------------------

alias box='/Users/tomm/vagrant'
alias localhost='cd /Users/tomm/Development/test-dev/d3; php -S localhost:8888'
alias branch='git rev-parse --abbrev-ref HEAD'

# Docker shortcuts ----------------------------------------

alias container="docker images -q $1"
alias dgc="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v /etc:/etc -e FORCE_IMAGE_REMOVAL=1 spotify/docker-gc"

function dls () {
    echo_yellow "\n- Networks ------------------------------------------------\n"
    docker network ls
    echo_yellow "\n- Containers ----------------------------------------------\n"
    docker ps -a
    echo_yellow "\n- Images --------------------------------------------------\n"
    docker images
    echo
}

function docker_stop_containers () {
    echo -e "\n> Stopping all containers"
    ids=$(docker ps -aq)
    if [ -n "${ids}" ]; then
        docker stop "$ids"
        echo_green "- Stopped containers"
    else
        echo_red "- No containers to stop"
    fi
}

function docker_remove_containers () {
    echo -e "\n> Removing all containers"
    docker ps -aq | xargs -n 1 -P 4 docker rm -f
}

function all_docker_network_ids() {
    docker network ls | grep "bridge" | grep -vE "bridge\s*bridge" | awk '/ / { print $1 }'
}

function docker_cleanup_volumes() {
    docker volume rm $(docker volume ls -qf dangling=true)
}

function docker_purge_networks() {
    echo -e "\n> Purging all networks"
    ids=$(all_docker_network_ids)
    if [ -n "${ids}" ]; then
        docker network rm $ids
        echo_green "- Removed networks"
    else
        echo_red "- No extra networks to remove"
    fi
}

alias docker_ls_empty_images="docker images | grep '<none>' | sed -E 's/ +/,/g' | cut -d ',' -f 3"

function docker_remove_empty_images () {
  docker_ls_empty_images | xargs docker rmi
}

function docker_cleanup () {
    docker_remove_containers
    docker_remove_empty_images
    docker_purge_networks
    docker_cleanup_volumes
    dls
}

alias de="docker exec $(container $1) -it bash"

# Git/dev coding helpers ----------------------------------

PREFER_EDITOR="cat $HOME/bin/preferred_editor.conf"

function preferred_editor () {
    echo -n "$1" > $HOME/bin/preferred_editor.conf
}

alias etl="echo $HOME/dev/identity-etl"
alias historical_enrichment="cd $HOME/dev/historical-enrichment && subl ."
alias pr="! sh -c '(git push origin $(git symbolic-ref --short -q HEAD) && hub pull-request)'"

# Misc. helper functions ----------------------------------

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

function convert_video() {
    infile="$1"
  
    basename="${infile%.*}"
    extension="${infile##*.}"
    outfile="${basename}.conv.mp4"
  
    echo "converting $infile -> $outfile"
  
    ffmpeg -y -i "${infile}" \
        -c:v libx265 \
        -preset fast \
        -b:v 5000k \
        -x265-params pass=1 \
        -an \
        -f mp4 \
        /dev/null && \
    ffmpeg -y -i "${infile}" \
        -c:v libx265 \
        -x265-params pass=2 \
        -preset medium \
        -b:v 5000k \
        -c:a aac \
        -b:a 320k \
        "${outfile}"
}

function rgb_to_hex() {
    echo $(ruby -pae '$_=?#+"%02X"*3%$F' <<< "$1 $2 $3")
}

function dlterraform() {
  if [ ! -z ${1} ] ; then
    (cd ${HOME}/bin && \
    wget "https://releases.hashicorp.com/terraform/${1}/terraform_${1}_darwin_amd64.zip" && \
    unzip -o terraform_$1_darwin_amd64.zip)
  else
    echo "Please input version number you wish to download for Terraform"
  fi
}

function ter() {
  case ${1} in
    "plan")  shift; cmd="terraform init && terraform plan -parallelism=100 ${@}";;
    "apply") shift; cmd="terraform init && terraform apply -auto-approve -parallelism=100 ${@}";;
    "dns")   cmd="grep fqdn terraform.tfstate | awk '{print \$2}' | tr -d '\"' | tr -d ','";;
    "ls")    cmd="terraform show | grep -E '^[a-zA-Z]' | tr -d ':'";;
    "sg")    cmd="grep -E '\"sg-(.*)' terraform.tfstate | awk '{print \$2}' | sort -u | tr -d '\"' | tr -d ','";;
    *)       cmd="terraform ${@}";;
  esac
  echo $cmd
  eval $cmd
}
